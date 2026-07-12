import { describe, expect, test } from "bun:test";
import type { GitHubExecutor } from "../src/github/writeback-service";
import { WritebackService } from "../src/github/writeback-service";
import { defaultSystemState } from "../src/control/state";
import { commentIntent, claimedTask, repository, SHA256 } from "./fixtures";
import { GitHubAppClient } from "../src/github/app-client";

class FakeExecutor implements GitHubExecutor {
  calls = 0;
  async execute() { this.calls += 1; return { resultUrl: "https://github.com/desync-organization/helios/issues/7#issuecomment-42", externalId: "42" }; }
}

function context(task = claimedTask(), overrides: Record<string, unknown> = {}) {
  return {
    task,
    repository: repository(),
    installationId: 123,
    state: { ...defaultSystemState(2_000), writebackMode: "live" as const },
    critic: { artifactId: "", reviewedArtifactId: "", reviewedContentHash: SHA256, verdict: "pass" as const, producerAgent: "reply", criticAgent: "critic" },
    now: 2_000,
    ...overrides,
  };
}

function prepared() {
  const task = claimedTask();
  const intent = commentIntent(task);
  const ctx = context(task);
  ctx.critic.artifactId = intent.criticArtifactId;
  ctx.critic.reviewedArtifactId = intent.artifactId;
  return { task, intent, ctx };
}

describe("credentialed write-back policy", () => {
  test("passed intent executes and persists a real result URL", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, ctx); expect(result.status).toBe("completed"); expect(result.resultUrl).toStartWith("https://github.com/"); expect(fake.calls).toBe(1); });
  test("idempotent replay returns the original URL exactly once", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const service = new WritebackService(fake); const first = await service.perform(intent, ctx); const second = await service.perform(intent, ctx); expect(second.resultUrl).toBe(first.resultUrl); expect(fake.calls).toBe(1); });
  test("global pause blocks the next mutation", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, state: { ...ctx.state, globalPaused: true } }); expect(result.status).toBe("denied"); expect(result.policyDecision.reasonCode).toBe("SYSTEM_PAUSED"); expect(fake.calls).toBe(0); });
  test("emergency mode blocks the next mutation", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, state: { ...ctx.state, emergencyMode: true } }); expect(result.policyDecision.reasonCode).toBe("SYSTEM_PAUSED"); });
  test("dry-run records no external completion", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, state: { ...ctx.state, writebackMode: "dry-run" } }); expect(result.status).toBe("dry_run"); expect(result.resultUrl).toBeUndefined(); expect(fake.calls).toBe(0); });
  test("repository mismatch cannot cross credentials", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, repository: repository({ repo: "other/repository" }) }); expect(result.policyDecision.reasonCode).toBe("REPOSITORY_MISMATCH"); });
  test("expired lease blocks write-back", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const expired = { ...ctx.task, lease: { ...ctx.task.lease!, expiresAt: 1_999 } }; const result = await new WritebackService(fake).perform(intent, { ...ctx, task: expired }); expect(result.policyDecision.reasonCode).toBe("LOST_LEASE"); });
  test("critic must pass the exact artifact hash", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, critic: { ...ctx.critic, reviewedContentHash: "b".repeat(64) } }); expect(result.policyDecision.reasonCode).toBe("CRITIC_MISMATCH"); });
  test("failed deterministic tests cannot be reasoned past", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform({ ...intent, testsPassed: false }, ctx); expect(result.policyDecision.reasonCode).toBe("QUALITY_GATES_FAILED"); });
  test("protected paths escalate before execution", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const branch = { ...intent, action: "branch_and_pr" as const, baseSha: "c".repeat(40), payload: { action: "branch_and_pr" as const, data: { branch: "hermes/fix", title: "Fix", body: "Tested fix", draft: false, files: [{ path: ".github/workflows/release.yml", content: "name: release", encoding: "utf-8" as const }] } } }; const task = { ...ctx.task, consentScope: { ...ctx.task.consentScope, allowedActions: ["branch_and_pr" as const] } }; const result = await new WritebackService(fake).perform(branch, { ...ctx, task }); expect(result.policyDecision.reasonCode).toBe("PROTECTED_PATH"); });
  test("read-only security audits cannot mutate", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const securityTask = { ...ctx.task, mode: "security_audit" as const }; const result = await new WritebackService(fake).perform(intent, { ...ctx, task: securityTask, state: { ...ctx.state, securityScanMode: "read-only" } }); expect(result.policyDecision.reasonCode).toBe("SECURITY_READ_ONLY"); });
  test("Git Data API stops when the default branch moved", async () => {
    const keys = await crypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]);
    const encoded = btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.exportKey("pkcs8", keys.privateKey))));
    const pem = `-----BEGIN PRIVATE KEY-----\n${encoded.match(/.{1,64}/g)!.join("\n")}\n-----END PRIVATE KEY-----`;
    let calls = 0;
    const fetcher = (async (url: string | URL | Request) => { calls += 1; const path = String(url); if (path.includes("access_tokens")) return Response.json({ token: "installation-token" }); if (path.includes("/git/ref/heads/main")) return Response.json({ object: { sha: "d".repeat(40) } }); throw new Error("No mutation should occur after a base conflict"); }) as typeof fetch;
    const client = new GitHubAppClient({ appId: "123", privateKeyPem: pem }, fetcher);
    const { intent } = prepared();
    const branch = { ...intent, action: "branch_and_pr" as const, baseSha: "c".repeat(40), payload: { action: "branch_and_pr" as const, data: { branch: "hermes/base-conflict", title: "Fix", body: "Tested fix", draft: false, files: [{ path: "src/fix.ts", content: "export const fixed = true;", encoding: "utf-8" as const }] } } };
    await expect(client.execute(branch, { installationId: 123, defaultBranch: "main", currentBaseSha: branch.baseSha })).rejects.toThrow("base branch changed");
    expect(calls).toBe(2);
  });
});
