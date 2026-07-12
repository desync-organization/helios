import { describe, expect, test } from "bun:test";
import { Artifact, ArtifactType, CriticVerdict } from "../packages/contracts/src/artifact";
import { newId, TaskId } from "../packages/contracts/src/ids";
import { Plan } from "../packages/contracts/src/plan";
import { RepositoryDescriptor } from "../packages/contracts/src/repository";
import { SecretFinding, VulnerabilityFinding } from "../packages/contracts/src/security";
import { Task } from "../packages/contracts/src/task";
import { TraceEvent } from "../packages/contracts/src/trace";
import { WritebackIntent } from "../packages/contracts/src/writeback";
import { commentIntent, GIT_SHA, repository, SHA256, task, trace } from "./fixtures";

describe("canonical contracts", () => {
  test("all 28 required artifact types are represented", () => expect(ArtifactType.options).toHaveLength(28));
  test("opaque IDs carry the required prefix", () => { const id = newId("task"); expect(id.startsWith("tsk_")).toBeTrue(); expect(TaskId.parse(id)).toBe(id); });
  test("unknown schema versions fail", () => expect(Task.safeParse({ ...task(), schemaVersion: 2 }).success).toBeFalse());
  test("unknown task fields fail", () => expect(Task.safeParse({ ...task(), rawToken: "forbidden" }).success).toBeFalse());
  test("task consent cannot cross repositories", () => expect(Task.safeParse({ ...task(), consentScope: { ...task().consentScope, repo: "other/repository" } }).success).toBeFalse());
  test("oversized task payload fails", () => expect(Task.safeParse({ ...task(), payload: "x".repeat(128_001) }).success).toBeFalse());
  test("repository descriptor is valid", () => expect(RepositoryDescriptor.parse(repository()).repo).toBe("desync-organization/helios"));
  test("plan rejects a missing dependency", () => {
    const plan = { schemaVersion: 1, artifactId: newId("artifact"), taskId: newId("task"), runId: newId("run"), plannerVersion: "v1", nodes: [{ nodeId: "node_a", role: "triage", dependsOn: ["node_missing"], acceptanceCriteria: ["valid"], toolGrants: [], budget: { timeoutMs: 1000, maxTokens: 100, maxCostUsd: 0 } }], createdAt: 1 };
    expect(Plan.safeParse(plan).success).toBeFalse();
  });
  test("plan rejects dependency cycles", () => { const node = (nodeId: string, dependsOn: string[]) => ({ nodeId, role: "test", dependsOn, acceptanceCriteria: ["valid"], toolGrants: [], budget: { timeoutMs: 1000, maxTokens: 100, maxCostUsd: 0 } }); const plan = { schemaVersion: 1, artifactId: newId("artifact"), taskId: newId("task"), runId: newId("run"), plannerVersion: "v1", nodes: [node("node_a", ["node_b"]), node("node_b", ["node_a"])], createdAt: 1 }; expect(Plan.safeParse(plan).success).toBeFalse(); });
  test("artifact requires a SHA-256 content hash", () => {
    const artifact = { schemaVersion: 1, artifactId: newId("artifact"), taskId: newId("task"), runId: newId("run"), nodeId: "node_a", type: "draft_reply", producer: { name: "reply", version: "v1" }, upstreamArtifactIds: [], policyRuleIds: [], contentHash: "bad", content: "reply", retentionClass: "standard", createdAt: 1 };
    expect(Artifact.safeParse(artifact).success).toBeFalse();
  });
  test("critic must be independent", () => expect(CriticVerdict.safeParse({ verdict: "pass", reviewedArtifactId: newId("artifact"), reviewedContentHash: SHA256, producerAgent: "same", criticAgent: "same", criteria: [{ criterion: "tests", passed: true, note: "passed" }] }).success).toBeFalse());
  test("trace preserves actual and equivalent costs separately", () => { const parsed = TraceEvent.parse(trace()); expect(parsed.costUsd).toBe(0); expect(parsed.costCloudEquivalentUsd).toBe(0.001); });
  test("write-back action must match its discriminated payload", () => { const claimed = { ...task(), lease: { ownerId: "x", token: "x".repeat(32), acquiredAt: 1, heartbeatAt: 1, expiresAt: 5 } }; const intent = commentIntent(claimed as any, { action: "labels_set" }); expect(WritebackIntent.safeParse(intent).success).toBeFalse(); });
  test("vulnerability findings separate severity, confidence, exploitability, and reachability", () => {
    const finding = { schemaVersion: 1, findingId: newId("finding"), scanner: "semgrep", scannerVersion: "1", ruleId: "rule", category: "sast", severity: "high", confidence: "medium", advisoryUrls: [], repo: "desync-organization/helios", commitSha: GIT_SHA, path: "src/a.ts", evidenceRedacted: "unsafe flow from request to query", evidenceFingerprint: SHA256, exploitability: "conditional", reachability: "potentially_reachable", recommendedFix: "Use a parameterized query", status: "open" };
    expect(VulnerabilityFinding.parse(finding).reachability).toBe("potentially_reachable");
  });
  test("secret findings have no field for a raw value", () => {
    const finding = SecretFinding.parse({ schemaVersion: 1, findingId: newId("finding"), repo: "desync-organization/helios", commitSha: GIT_SHA, detector: "gitleaks", secretType: "api_key", path: ".env", fingerprint: SHA256, redactedPrefix: "abcd", redactedSuffix: "wxyz", rotationRecommended: true, remediationState: "open" });
    expect("value" in finding).toBeFalse();
  });
});
