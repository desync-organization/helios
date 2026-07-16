import { ControlPlaneError } from "../../../src/errors";
import type { NormalizedWebhook } from "./normalize";
import type { WorkerEnv } from "./types";

async function controlRequest(env: WorkerEnv, path: string, body: unknown, token = env.CONTROL_PLANE_INGEST_TOKEN): Promise<Response> {
  const response = await fetch(`${env.CONTROL_PLANE_URL.replace(/\/$/, "")}${path}`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(body) });
  if (!response.ok) {
    const payload = await response.clone().json().catch(() => ({})) as { error?: { code?: string; message?: string; retryable?: boolean } };
    const code = response.status === 401 ? "UNAUTHENTICATED"
      : response.status === 403 ? "POLICY_DENIED"
        : response.status === 409 ? "CONFLICT"
          : response.status === 413 ? "TOO_LARGE"
            : response.status === 422 ? "VALIDATION_FAILED"
              : response.status === 429 ? "RATE_LIMITED"
                : "UPSTREAM_FAILED";
    throw new ControlPlaneError(code, payload.error?.message ?? `Control plane returned ${response.status}`, response.status, payload.error?.retryable ?? (response.status >= 500 || response.status === 429), payload.error?.code ? { reasonCode: payload.error.code } : undefined);
  }
  return response;
}

export interface WritebackReservation {
  ok: boolean;
  replay: boolean;
  status: "pending" | "dry_run" | "completed";
  reason?: string;
  installationId?: string;
  defaultBranch?: string;
  resultUrl?: string;
  externalId?: string;
  policyDecision?: {
    allowed: boolean;
    reasonCode: string;
    message: string;
    ruleIds: string[];
  };
}

export async function reserveWriteback(env: WorkerEnv, intent: unknown, leaseToken: string): Promise<WritebackReservation> {
  const response = await controlRequest(env, "/writeback/reserve", { intent, leaseToken });
  return response.json() as Promise<WritebackReservation>;
}

export async function completeWriteback(env: WorkerEnv, writebackId: string, resultUrl: string, externalId: string): Promise<void> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try { await controlRequest(env, "/writeback/complete", { writebackId, resultUrl, externalId }); return; }
    catch (error) {
      lastError = error;
      if (!(error instanceof ControlPlaneError) || !error.retryable || attempt === 4) break;
      await new Promise((resolve) => setTimeout(resolve, 100 * 2 ** attempt));
    }
  }
  throw lastError;
}

export async function failWriteback(env: WorkerEnv, writebackId: string, message: string): Promise<void> {
  await controlRequest(env, "/writeback/fail", { writebackId, error: { code: "GITHUB_WRITEBACK_FAILED", message: message.slice(0, 1_024), retryable: true } }).catch(() => undefined);
}

export async function ingestWebhook(env: WorkerEnv, webhook: NormalizedWebhook): Promise<void> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try { await controlRequest(env, "/ingest/github", webhook); return; }
    catch (error) {
      lastError = error;
      if (attempt < 2) await new Promise((resolve) => setTimeout(resolve, 50 * 2 ** attempt));
    }
  }
  await recordDeadLetter(env, webhook, lastError instanceof Error ? lastError.message : "unknown ingest error");
  throw lastError;
}

export async function recordDeadLetter(env: WorkerEnv, webhook: NormalizedWebhook, reason: string): Promise<void> {
  await controlRequest(env, "/ingest/dead-letter", { schemaVersion: 1, deliveryId: webhook.deliveryId, repo: webhook.repo, event: webhook.event, reason: reason.slice(0, 1_024), payloadRedacted: webhook.payloadRedacted, normalized: webhook, createdAt: Date.now() }).catch(() => undefined);
}

export async function forwardRuntimeRequest(env: WorkerEnv, request: Request): Promise<Response> {
  const target = new URL(request.url);
  return fetch(`${env.CONTROL_PLANE_URL.replace(/\/$/, "")}${target.pathname}${target.search}`, { method: request.method, headers: { Authorization: `Bearer ${env.CONTROL_PLANE_INGEST_TOKEN}`, "Content-Type": request.headers.get("Content-Type") ?? "application/json", "Idempotency-Key": request.headers.get("Idempotency-Key") ?? crypto.randomUUID() }, body: request.method === "GET" ? undefined : request.body });
}

export async function authorizeProvider(env: WorkerEnv, body: Record<string, unknown>): Promise<Record<string, unknown>> {
  const response = await controlRequest(env, "/providers/authorize", body);
  return response.json() as Promise<Record<string, unknown>>;
}

export async function auditProviderCall(env: WorkerEnv, body: Record<string, unknown>): Promise<void> { await controlRequest(env, "/providers/audit", body); }
