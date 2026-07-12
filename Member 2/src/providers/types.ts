import type { DataClassification } from "../../packages/contracts/src/common";
import type { ProviderName, RepoSlug } from "../../packages/contracts/src/repository";
import type { ConsentScope } from "../../packages/contracts/src/task";

export type ProviderPurpose = "triage" | "reply" | "research" | "vulnerability_intelligence" | "transcription" | "alert_speech" | "standup_digest";

export interface ProviderRequest {
  taskId: string;
  repo: RepoSlug;
  purpose: ProviderPurpose;
  provider: ProviderName;
  content: string;
  schema?: Record<string, unknown>;
  classification: DataClassification;
  consent: ConsentScope;
}

export interface ProviderResult {
  provider: ProviderName;
  model: string;
  output: string;
  tokensIn: number;
  tokensOut: number;
  latencyMs: number;
  costUsd: number;
  requestId: string;
  sourceUrls?: string[];
  retrievedAt?: number;
}

export interface ProviderCallAudit {
  taskId: string;
  repo: RepoSlug;
  provider: ProviderName;
  purpose: ProviderPurpose;
  consentRef: string;
  classification: DataClassification;
  bytesSent: number;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  requestId: string;
  createdAt: number;
}
