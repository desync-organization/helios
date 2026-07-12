import { readBoundedJson, requireBearer } from "../../../src/auth";
import { ControlPlaneError } from "../../../src/errors";
import { GitHubAppClient } from "../../../src/github/app-client";
import { WritebackIntent } from "../../../packages/contracts/src/writeback";
import { completeWriteback, failWriteback, reserveWriteback } from "./control-plane-client";
import type { WorkerEnv } from "./types";

export async function handleWriteback(request: Request, env: WorkerEnv): Promise<Response> {
  await requireBearer(request, env.RUNTIME_BEARER_TOKEN);
  const raw = await readBoundedJson<{ intent: unknown; leaseToken: string }>(request, 2_500_000);
  const parsed = WritebackIntent.safeParse(raw.intent);
  if (!parsed.success || typeof raw.leaseToken !== "string") throw new ControlPlaneError("VALIDATION_FAILED", "Invalid write-back intent", 422, false, { issues: parsed.success ? [] : parsed.error.issues.map((issue) => ({ path: issue.path.join("."), message: issue.message })) });
  const reservation = await reserveWriteback(env, parsed.data, raw.leaseToken);
  const client = new GitHubAppClient({ appId: env.GITHUB_APP_ID, privateKeyPem: env.GITHUB_APP_PRIVATE_KEY });
  try {
    const result = await client.execute(parsed.data, { installationId: Number(reservation.installationId), defaultBranch: reservation.defaultBranch, currentBaseSha: parsed.data.baseSha });
    await completeWriteback(env, parsed.data.writebackId, result.resultUrl, result.externalId);
    return Response.json({ schemaVersion: 1, writebackId: parsed.data.writebackId, status: "completed", resultUrl: result.resultUrl, externalId: result.externalId });
  } catch (error) {
    await failWriteback(env, parsed.data.writebackId, error instanceof Error ? error.message : "GitHub write-back failed");
    throw error;
  }
}
