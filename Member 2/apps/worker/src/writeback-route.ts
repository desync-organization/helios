import { readBoundedJson, requireBearer } from "../../../src/auth";
import { ControlPlaneError } from "../../../src/errors";
import { GitHubAppClient } from "../../../src/github/app-client";
import { WritebackIntent } from "../../../packages/contracts/src/writeback";
import { completeWriteback, failWriteback, reserveWriteback, type WritebackReservation } from "./control-plane-client";
import type { WorkerEnv } from "./types";

export interface WritebackDependencies {
  reserve(env: WorkerEnv, intent: unknown, leaseToken: string): Promise<WritebackReservation>;
  complete(env: WorkerEnv, writebackId: string, resultUrl: string, externalId: string): Promise<void>;
  fail(env: WorkerEnv, writebackId: string, message: string): Promise<void>;
  execute(intent: WritebackIntent, reservation: WritebackReservation, env: WorkerEnv): Promise<{ resultUrl: string; externalId: string }>;
}

const defaultDependencies: WritebackDependencies = {
  reserve: reserveWriteback,
  complete: completeWriteback,
  fail: failWriteback,
  async execute(intent, reservation, env) {
    if (!reservation.installationId || !/^\d+$/.test(reservation.installationId) || !reservation.defaultBranch) throw new ControlPlaneError("UPSTREAM_FAILED", "Control plane returned an invalid write-back reservation", 502, false);
    const client = new GitHubAppClient({ appId: env.GITHUB_APP_ID, privateKeyPem: env.GITHUB_APP_PRIVATE_KEY });
    return client.execute(intent, { installationId: Number(reservation.installationId), defaultBranch: reservation.defaultBranch, currentBaseSha: intent.baseSha });
  },
};

export async function handleWriteback(request: Request, env: WorkerEnv, dependencies: WritebackDependencies = defaultDependencies): Promise<Response> {
  await requireBearer(request, env.RUNTIME_BEARER_TOKEN);
  const raw = await readBoundedJson<{ intent: unknown; leaseToken: string }>(request, 2_500_000);
  const parsed = WritebackIntent.safeParse(raw.intent);
  if (!parsed.success || typeof raw.leaseToken !== "string") throw new ControlPlaneError("VALIDATION_FAILED", "Invalid write-back intent", 422, false, { issues: parsed.success ? [] : parsed.error.issues.map((issue) => ({ path: issue.path.join("."), message: issue.message })) });
  const reservation = await dependencies.reserve(env, parsed.data, raw.leaseToken);
  if (reservation.status === "dry_run") {
    return Response.json({
      schemaVersion: 1,
      writebackId: parsed.data.writebackId,
      status: "dry_run",
      policyDecision: reservation.policyDecision ?? {
        allowed: false,
        reasonCode: "DRY_RUN",
        message: "Dry-run mode recorded the write-back intent without an external mutation",
        ruleIds: ["autonomy.dry-run"],
      },
    });
  }
  if (reservation.replay && reservation.status === "completed") {
    if (!reservation.resultUrl?.startsWith("https://") || !reservation.externalId) throw new ControlPlaneError("UPSTREAM_FAILED", "Completed write-back replay is missing its persisted result", 502, false);
    return Response.json({ schemaVersion: 1, writebackId: parsed.data.writebackId, status: "completed", resultUrl: reservation.resultUrl, externalId: reservation.externalId, replay: true });
  }
  if (!reservation.ok || reservation.status !== "pending") throw new ControlPlaneError("POLICY_DENIED", "Write-back reservation was not authorized", 403, false, { reasonCode: reservation.reason ?? "DENIED" });
  let result: { resultUrl: string; externalId: string };
  try {
    result = await dependencies.execute(parsed.data, reservation, env);
  } catch (error) {
    await dependencies.fail(env, parsed.data.writebackId, error instanceof Error ? error.message : "GitHub write-back failed");
    throw error;
  }
  try {
    await dependencies.complete(env, parsed.data.writebackId, result.resultUrl, result.externalId);
  } catch {
    // The external mutation already happened. Leave the canonical action pending
    // for idempotent reconciliation; never record a false external failure.
    throw new ControlPlaneError("UPSTREAM_FAILED", "GitHub result persistence is pending reconciliation", 503, true, { externalMutationCompleted: true });
  }
  return Response.json({ schemaVersion: 1, writebackId: parsed.data.writebackId, status: "completed", resultUrl: result.resultUrl, externalId: result.externalId });
}
