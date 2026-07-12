import { SCHEMA_VERSION } from "../packages/contracts/src/common";
import { newId } from "../packages/contracts/src/ids";
import type { RepositoryDescriptor } from "../packages/contracts/src/repository";
import type { Task } from "../packages/contracts/src/task";
import type { TraceEvent } from "../packages/contracts/src/trace";
import type { WritebackIntent } from "../packages/contracts/src/writeback";

export const SHA256 = "a".repeat(64);
export const OTHER_SHA256 = "b".repeat(64);
export const GIT_SHA = "c".repeat(40);

export function repository(overrides: Partial<RepositoryDescriptor> = {}): RepositoryDescriptor {
  return {
    schemaVersion: SCHEMA_VERSION,
    repo: "desync-organization/helios",
    defaultBranch: "main",
    visibility: "public",
    writebackOptIn: true,
    securityAuditOptIn: true,
    allowedActions: ["comment", "labels_set", "milestone_set", "duplicate_close", "branch_and_pr", "build_branch_and_pr", "security_pr", "pr_review_comment", "pr_merge", "release_draft", "sarif_upload", "build_status_comment"],
    allowedCloudProviders: ["workers_ai", "haiku", "linkup"],
    protectedPaths: [".github/workflows/**", "policy/production/**"],
    sizeLimits: { maxPatchBytes: 100_000, maxFiles: 20 },
    requiredChecks: ["test"],
    activePolicyVersion: "2.0.0",
    retentionPolicy: { artifactDays: 90, entityDays: 30, providerPayloadHours: 0, voiceAudioMinutes: 0, scannerOutputHours: 24 },
    health: "healthy",
    updatedAt: 1_000,
    ...overrides,
  };
}

export function task(overrides: Partial<Task> = {}): Task {
  const now = overrides.createdAt ?? 1_000;
  return {
    schemaVersion: SCHEMA_VERSION,
    taskId: newId("task", now),
    source: { kind: "operator", promptId: "prompt-1" },
    mode: "maintain",
    type: "respond",
    repo: "desync-organization/helios",
    payload: "Please respond to issue 7",
    status: "pending",
    dedupeKey: "operator:prompt-1",
    requestedBy: "operator",
    consentScope: { repo: "desync-organization/helios", allowedActions: ["comment", "branch_and_pr", "security_pr"], allowedCloudProviders: ["workers_ai", "haiku", "linkup"], privateCodeMayLeaveDevice: false, externalSecurityUploadAllowed: false, expiresAt: now + 100_000, grantedBy: "operator", consentRef: "consent-1" },
    dataClassification: "public",
    policyVersion: "2.0.0",
    resultUrls: [],
    createdAt: now,
    updatedAt: now,
    ...overrides,
  };
}

export function claimedTask(now = 2_000, overrides: Partial<Task> = {}): Task {
  return task({ status: "running", lease: { ownerId: "runtime-1", token: "lease-token-that-is-at-least-thirty-two-characters", acquiredAt: now - 100, heartbeatAt: now - 50, expiresAt: now + 10_000 }, createdAt: now - 1_000, updatedAt: now, ...overrides });
}

export function trace(sequence = 1, overrides: Partial<TraceEvent> = {}): TraceEvent {
  return {
    schemaVersion: 1,
    eventId: newId("event"), taskId: newId("task"), runId: newId("run"), spanId: newId("span"), sequence,
    nodeId: "node_triage", agent: "triage", model: { baseModel: "Qwen3-4B", baseRevision: "rev-1", baseSha256: SHA256, quantization: "Q4_K_M", promptVersion: "v1", agentVersion: "agents-v1" },
    promptHash: SHA256, inputArtifactRefs: [], tokensIn: 10, tokensOut: 5, costUsd: 0, costCloudEquivalentUsd: 0.001,
    latencyMs: 100, executionLocation: "local_gpu", toolCalls: [], status: "succeeded", startedAt: 1_000, finishedAt: 1_100,
    ...overrides,
  };
}

export function commentIntent(taskValue: Task, overrides: Partial<WritebackIntent> = {}): WritebackIntent {
  const artifactId = newId("artifact");
  return {
    schemaVersion: 1, writebackId: newId("writeback"), taskId: taskValue.taskId, runId: newId("run"), repo: taskValue.repo,
    action: "comment", idempotencyKey: "idempotency-key-00000001", leaseToken: taskValue.lease!.token, artifactId, artifactHash: SHA256,
    criticArtifactId: newId("artifact"), policyRuleIds: ["autonomy.critic.exact-hash"], requiredChecksPassed: true,
    securityChecksPassed: true, testsPassed: true, breakingChange: false, requestedAt: 2_000,
    payload: { action: "comment", data: { issueNumber: 7, body: "Verified response with repository evidence." } },
    ...overrides,
  };
}
