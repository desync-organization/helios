import { readBoundedJson, requireBearer } from "../../../src/auth";
import { ControlPlaneError } from "../../../src/errors";
import { redactSensitive } from "../../../src/security/redaction";
import { auditProviderCall, authorizeProvider } from "./control-plane-client";
import type { WorkerEnv } from "./types";

interface ProxyBody { taskId: string; repo: string; purpose: string; content: string; schema?: Record<string, unknown>; provider?: string }

async function callConfiguredProvider(env: WorkerEnv, body: ProxyBody, provider: "workers_ai" | "haiku" | "linkup"): Promise<Record<string, unknown>> {
  const configs = {
    workers_ai: [env.WORKERS_AI_ENDPOINT, env.WORKERS_AI_TOKEN],
    haiku: [env.HAIKU_ENDPOINT, env.HAIKU_API_KEY],
    linkup: [env.LINKUP_ENDPOINT, env.LINKUP_API_KEY],
  } as const;
  const [endpoint, token] = configs[provider];
  if (!endpoint || !token) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", `${provider} is not configured`, 503, true);
  const startedAt = Date.now();
  const requestPayload = provider === "linkup" ? { query: body.content, includeSources: true } : { messages: [{ role: "user", content: body.content }], response_format: body.schema ? { type: "json_schema", json_schema: body.schema } : undefined, tools: [] };
  const response = await fetch(endpoint, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify(requestPayload) });
  if (!response.ok) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", `${provider} returned ${response.status}`, 503, true);
  const result = await response.json() as Record<string, unknown>;
  return { provider, exactModel: String(result.model ?? (provider === "linkup" ? "research" : "configured")), result, tokens: result.usage ?? {}, latencyMs: Date.now() - startedAt, costUsd: Number(result.cost_usd ?? 0), requestId: String(result.id ?? crypto.randomUUID()), executionLocation: "remote_provider" };
}

export async function handleProviderProxy(request: Request, env: WorkerEnv, kind: "inference" | "research"): Promise<Response> {
  await requireBearer(request, env.PROVIDER_PROXY_TOKEN);
  const body = await readBoundedJson<ProxyBody>(request, 131_072);
  if (!body.taskId || !body.repo || !body.purpose || typeof body.content !== "string" || typeof body.provider !== "string") throw new ControlPlaneError("VALIDATION_FAILED", "An explicit provider and all request fields are required", 422, false);
  const authorized = await authorizeProvider(env, { schemaVersion: 1, taskId: body.taskId, repo: body.repo, purpose: body.purpose, requestedProvider: body.provider, kind });
  if (authorized.allowed !== true) throw new ControlPlaneError("FORBIDDEN", "Canonical consent denied this provider request", 403, false);
  const redacted = await redactSensitive(body.content, true);
  if (new TextEncoder().encode(redacted.value).byteLength > 131_072) throw new ControlPlaneError("TOO_LARGE", "Provider content exceeds limit", 413, false);
  const allowedForKind = kind === "research" ? ["linkup"] : ["workers_ai", "haiku"];
  if (!allowedForKind.includes(body.provider) || !Array.isArray(authorized.providers) || !authorized.providers.includes(body.provider)) throw new ControlPlaneError("FORBIDDEN", "Requested provider is not consented for this operation", 403, false);
  const providers = [body.provider] as Array<"workers_ai" | "haiku" | "linkup">;
  let lastError: unknown;
  for (const provider of providers) {
    try {
      const result = await callConfiguredProvider(env, { ...body, content: redacted.value }, provider);
      await auditProviderCall(env, { schemaVersion: 1, taskId: body.taskId, repo: body.repo, provider, purpose: body.purpose, consentRef: authorized.consentRef, classification: authorized.classification, bytesSent: new TextEncoder().encode(redacted.value).byteLength, ...result, createdAt: Date.now() });
      return Response.json(result);
    } catch (error) { lastError = error; }
  }
  throw lastError ?? new ControlPlaneError("PROVIDER_UNAVAILABLE", "No provider is configured", 503, true);
}

interface VoiceBody { taskId: string; repo: string; classification: "public" | "internal" | "private" | "restricted"; audioBase64?: string; text?: string; purpose: "transcription" | "alert_speech" | "standup_digest" }

export async function handleVoice(request: Request, env: WorkerEnv, operation: "transcribe" | "speak"): Promise<Response> {
  await requireBearer(request, env.PROVIDER_PROXY_TOKEN);
  const body = await readBoundedJson<VoiceBody>(request, 1_500_000);
  if (!env.ELEVENLABS_ENDPOINT || !env.ELEVENLABS_API_KEY) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", "ElevenLabs is not configured", 503, true);
  if (operation === "transcribe" && body.purpose !== "transcription") throw new ControlPlaneError("VALIDATION_FAILED", "Transcription purpose is required", 422, false);
  if (operation === "speak" && !["alert_speech", "standup_digest"].includes(body.purpose)) throw new ControlPlaneError("VALIDATION_FAILED", "Unsafe speech purpose", 422, false);
  if (operation === "speak" && !["public", "internal"].includes(body.classification)) throw new ControlPlaneError("FORBIDDEN", "Private or restricted content cannot be spoken", 403, false);
  const authorized = await authorizeProvider(env, { schemaVersion: 1, taskId: body.taskId, repo: body.repo, purpose: body.purpose, requestedProvider: "elevenlabs", kind: "voice" });
  if (authorized.allowed !== true) throw new ControlPlaneError("FORBIDDEN", "Canonical consent denied voice provider use", 403, false);
  const startedAt = Date.now();
  let response: Response;
  let bytesSent = 0;
  if (operation === "transcribe") {
    if (!body.audioBase64 || body.audioBase64.length > 1_400_000) throw new ControlPlaneError("TOO_LARGE", "Audio exceeds the bounded transcription limit", 413, false);
    const bytes = Uint8Array.from(atob(body.audioBase64), (character) => character.charCodeAt(0));
    bytesSent = bytes.byteLength;
    const form = new FormData();
    form.set("file", new Blob([bytes], { type: "audio/webm" }), "transient.webm");
    form.set("model_id", "scribe_v1");
    response = await fetch(`${env.ELEVENLABS_ENDPOINT.replace(/\/$/, "")}/speech-to-text`, { method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY }, body: form });
  } else {
    const redacted = await redactSensitive(body.text ?? "", true);
    if (redacted.findings.length || redacted.value.length > 2_000) throw new ControlPlaneError("FORBIDDEN", "Speech contains sensitive or oversized content", 403, false);
    bytesSent = new TextEncoder().encode(redacted.value).byteLength;
    response = await fetch(`${env.ELEVENLABS_ENDPOINT.replace(/\/$/, "")}/text-to-speech`, { method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY, "Content-Type": "application/json" }, body: JSON.stringify({ text: redacted.value, model_id: "eleven_multilingual_v2" }) });
  }
  if (!response.ok) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", `ElevenLabs returned ${response.status}`, 503, true);
  const requestId = response.headers.get("request-id") ?? crypto.randomUUID();
  await auditProviderCall(env, { schemaVersion: 1, taskId: body.taskId, repo: body.repo, provider: "elevenlabs", purpose: body.purpose, consentRef: authorized.consentRef, classification: body.classification, bytesSent, tokensIn: 0, tokensOut: 0, costUsd: 0, requestId, latencyMs: Date.now() - startedAt, status: "completed", createdAt: Date.now() });
  if (operation === "transcribe") {
    const result = await response.json() as { text?: string };
    return Response.json({ transcript: result.text ?? "", confirmationRequired: true, rawAudioRetained: false, requestId });
  }
  return Response.json({ spoken: true, textFallback: body.text, requestId });
}
