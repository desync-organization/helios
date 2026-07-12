import { ProviderName, type RepositoryDescriptor } from "../../packages/contracts/src/repository";
import { ControlPlaneError } from "../errors";
import { redactSensitive } from "../security/redaction";
import type { ProviderCallAudit, ProviderRequest, ProviderResult } from "./types";

export interface ProviderAdapter { invoke(request: ProviderRequest & { content: string }): Promise<ProviderResult> }

export class EgressController {
  readonly audit: ProviderCallAudit[] = [];
  constructor(private readonly adapters: Partial<Record<ProviderName, ProviderAdapter>>) {}

  async invoke(request: ProviderRequest, repository: RepositoryDescriptor, now = Date.now()): Promise<ProviderResult> {
    ProviderName.parse(request.provider);
    if (request.repo !== repository.repo || request.consent.repo !== request.repo) throw new ControlPlaneError("FORBIDDEN", "Repository identity mismatch", 403, false);
    if (request.consent.expiresAt <= now) throw new ControlPlaneError("FORBIDDEN", "Data-egress consent expired", 403, false);
    if (!repository.allowedCloudProviders.includes(request.provider) || !request.consent.allowedCloudProviders.includes(request.provider)) throw new ControlPlaneError("FORBIDDEN", "Provider is not consented for this repository and task", 403, false);
    if (repository.visibility !== "public" && !request.consent.privateCodeMayLeaveDevice) throw new ControlPlaneError("FORBIDDEN", "Private repository content is local-only", 403, false);
    if (request.purpose === "vulnerability_intelligence" && !request.consent.externalSecurityUploadAllowed) throw new ControlPlaneError("FORBIDDEN", "External security upload is not consented", 403, false);
    const redacted = await redactSensitive(request.content, true);
    const bytes = new TextEncoder().encode(redacted.value).byteLength;
    if (bytes > 131_072) throw new ControlPlaneError("TOO_LARGE", "Provider request exceeds 128 KiB", 413, false);
    const adapter = this.adapters[request.provider];
    if (!adapter) throw new ControlPlaneError("PROVIDER_UNAVAILABLE", "Provider is not configured", 503, true);
    const result = await adapter.invoke({ ...request, content: redacted.value });
    this.audit.push({ taskId: request.taskId, repo: request.repo, provider: result.provider, purpose: request.purpose, consentRef: request.consent.consentRef, classification: request.classification, bytesSent: bytes, tokensIn: result.tokensIn, tokensOut: result.tokensOut, costUsd: result.costUsd, requestId: result.requestId, createdAt: now });
    return result;
  }
}
