import { requireBearer } from "../../../src/auth";
import { safeErrorResponse } from "../../../src/errors";
import { FixedWindowRateLimiter } from "../../../src/rate-limit";
import { forwardRuntimeRequest, ingestWebhook } from "./control-plane-client";
import { isHermesAuthored, normalizeGitHubWebhook } from "./normalize";
import { handleProviderProxy, handleVoice } from "./provider-routes";
import { verifyGitHubSignature } from "./signature";
import { handleWriteback } from "./writeback-route";
import type { ExecutionContextLike, WorkerEnv } from "./types";

const runtimeLimiter = new FixedWindowRateLimiter(120, 60_000);
const providerLimiter = new FixedWindowRateLimiter(20, 60_000);

async function route(request: Request, env: WorkerEnv, context: ExecutionContextLike): Promise<Response> {
  const url = new URL(request.url);
  if (url.pathname === "/status" && request.method === "GET") return Response.json({ status: "ok", service: "hermes-ingress", environment: env.ENVIRONMENT, timestamp: Date.now() });
  if (url.pathname === "/webhooks/github" && request.method === "POST") {
    const rawBody = await request.arrayBuffer();
    if (rawBody.byteLength > 2_000_000) return Response.json({ error: { code: "TOO_LARGE", message: "Webhook exceeds 2 MB", retryable: false } }, { status: 413 });
    if (!(await verifyGitHubSignature(rawBody, request.headers.get("X-Hub-Signature-256"), env.GITHUB_WEBHOOK_SECRET))) return Response.json({ error: { code: "UNAUTHENTICATED", message: "Invalid webhook signature", retryable: false } }, { status: 401 });
    const event = request.headers.get("X-GitHub-Event") ?? "";
    const deliveryId = request.headers.get("X-GitHub-Delivery") ?? "";
    if (!deliveryId || deliveryId.length > 128) return Response.json({ error: { code: "VALIDATION_FAILED", message: "Missing delivery ID", retryable: false } }, { status: 422 });
    let payload: Record<string, unknown>;
    try { payload = JSON.parse(new TextDecoder().decode(rawBody)) as Record<string, unknown>; } catch { return Response.json({ error: { code: "VALIDATION_FAILED", message: "Invalid JSON", retryable: false } }, { status: 422 }); }
    if (isHermesAuthored(payload, env.HERMES_BOT_LOGIN)) return Response.json({ accepted: false, reason: "bot_loop_suppressed" }, { status: 202 });
    const normalized = await normalizeGitHubWebhook(event, deliveryId, payload);
    if (!normalized) return Response.json({ accepted: false, reason: "unsupported_event" }, { status: 202 });
    context.waitUntil(ingestWebhook(env, normalized));
    return Response.json({ accepted: true, deliveryId }, { status: 202 });
  }
  if (url.pathname === "/runtime/writeback" && request.method === "POST") {
    runtimeLimiter.consume(request.headers.get("CF-Connecting-IP") ?? "runtime");
    return handleWriteback(request, env);
  }
  if (url.pathname.startsWith("/runtime/")) {
    runtimeLimiter.consume(request.headers.get("CF-Connecting-IP") ?? "runtime");
    await requireBearer(request, env.RUNTIME_BEARER_TOKEN);
    return forwardRuntimeRequest(env, request);
  }
  if (url.pathname === "/providers/inference" && request.method === "POST") {
    providerLimiter.consume(request.headers.get("CF-Connecting-IP") ?? "provider");
    return handleProviderProxy(request, env, "inference");
  }
  if (url.pathname === "/providers/research" && request.method === "POST") {
    providerLimiter.consume(request.headers.get("CF-Connecting-IP") ?? "provider");
    return handleProviderProxy(request, env, "research");
  }
  if (url.pathname === "/voice/transcribe" && request.method === "POST") {
    providerLimiter.consume(request.headers.get("CF-Connecting-IP") ?? "voice");
    return handleVoice(request, env, "transcribe");
  }
  if (url.pathname === "/voice/speak" && request.method === "POST") {
    providerLimiter.consume(request.headers.get("CF-Connecting-IP") ?? "voice");
    return handleVoice(request, env, "speak");
  }
  return Response.json({ error: { code: "NOT_FOUND", message: "Route not found", retryable: false } }, { status: 404 });
}

export default {
  async fetch(request: Request, env: WorkerEnv, context: ExecutionContextLike): Promise<Response> {
    try { return await route(request, env, context); } catch (error) { return safeErrorResponse(error); }
  },
  async scheduled(_controller: ScheduledController, env: WorkerEnv): Promise<void> {
    await fetch(`${env.CONTROL_PLANE_URL.replace(/\/$/, "")}/maintenance/retry-dead-letters`, { method: "POST", headers: { Authorization: `Bearer ${env.CONTROL_PLANE_INGEST_TOKEN}` } });
  },
};
