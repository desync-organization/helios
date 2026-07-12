import { ControlPlaneError } from "../errors";
import type { ProviderAdapter } from "./egress";
import type { ProviderRequest, ProviderResult } from "./types";

interface HttpProviderConfig { endpoint: string; apiKey: string; model: string; provider: "workers_ai" | "haiku" }

export class HostedInferenceAdapter implements ProviderAdapter {
  constructor(private readonly config: HttpProviderConfig, private readonly fetcher: typeof fetch = fetch) {}
  async invoke(request: ProviderRequest & { content: string }): Promise<ProviderResult> {
    const startedAt = Date.now();
    const response = await this.fetcher(this.config.endpoint, {
      method: "POST",
      headers: { Authorization: `Bearer ${this.config.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: this.config.model, messages: [{ role: "user", content: request.content }], response_format: request.schema ? { type: "json_schema", json_schema: request.schema } : undefined, tools: [] }),
    });
    if (!response.ok) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", `${this.config.provider} returned ${response.status}`, 503, true);
    const body = await response.json() as { id?: string; result?: { response?: string }; choices?: Array<{ message?: { content?: string } }>; usage?: { prompt_tokens?: number; completion_tokens?: number }; cost_usd?: number };
    const output = body.result?.response ?? body.choices?.[0]?.message?.content;
    if (typeof output !== "string") throw new ControlPlaneError("UPSTREAM_FAILED", "Provider returned no usable output", 502, true);
    return { provider: this.config.provider, model: this.config.model, output, tokensIn: body.usage?.prompt_tokens ?? 0, tokensOut: body.usage?.completion_tokens ?? 0, latencyMs: Date.now() - startedAt, costUsd: body.cost_usd ?? 0, requestId: body.id ?? crypto.randomUUID() };
  }
}

interface ResearchConfig { endpoint: string; apiKey: string; provider: "linkup" | "osv" | "github_advisory" }
export class ResearchAdapter implements ProviderAdapter {
  constructor(private readonly config: ResearchConfig, private readonly fetcher: typeof fetch = fetch) {}
  async invoke(request: ProviderRequest & { content: string }): Promise<ProviderResult> {
    const startedAt = Date.now();
    const response = await this.fetcher(this.config.endpoint, { method: "POST", headers: { Authorization: `Bearer ${this.config.apiKey}`, "Content-Type": "application/json" }, body: JSON.stringify({ query: request.content.slice(0, 4_096), depth: "standard", includeSources: true }) });
    if (!response.ok) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", `${this.config.provider} returned ${response.status}`, 503, true);
    const body = await response.json() as { id?: string; answer?: string; sources?: Array<{ url?: string }>; cost_usd?: number };
    if (!body.answer) throw new ControlPlaneError("UPSTREAM_FAILED", "Research provider returned no answer", 502, true);
    return { provider: this.config.provider, model: "research", output: body.answer, tokensIn: 0, tokensOut: 0, latencyMs: Date.now() - startedAt, costUsd: body.cost_usd ?? 0, requestId: body.id ?? crypto.randomUUID(), sourceUrls: (body.sources ?? []).flatMap((source) => source.url?.startsWith("https://") ? [source.url] : []), retrievedAt: Date.now() };
  }
}

export class ElevenLabsAdapter implements ProviderAdapter {
  constructor(private readonly apiKey: string, private readonly endpoint: string, private readonly fetcher: typeof fetch = fetch) {}
  async invoke(request: ProviderRequest & { content: string }): Promise<ProviderResult> {
    if (request.purpose !== "alert_speech" && request.purpose !== "standup_digest") throw new ControlPlaneError("FORBIDDEN", "This voice route accepts safe speech purposes only", 403, false);
    if (request.classification !== "public" && request.classification !== "internal") throw new ControlPlaneError("FORBIDDEN", "Restricted/private content cannot be spoken", 403, false);
    const startedAt = Date.now();
    const response = await this.fetcher(this.endpoint, { method: "POST", headers: { "xi-api-key": this.apiKey, "Content-Type": "application/json" }, body: JSON.stringify({ text: request.content.slice(0, 2_000) }) });
    if (!response.ok) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", `ElevenLabs returned ${response.status}`, 503, true);
    return { provider: "elevenlabs", model: "eleven_multilingual_v2", output: "speech_generated", tokensIn: 0, tokensOut: 0, latencyMs: Date.now() - startedAt, costUsd: 0, requestId: response.headers.get("request-id") ?? crypto.randomUUID() };
  }
}
