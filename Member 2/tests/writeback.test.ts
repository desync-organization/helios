import { describe, expect, test } from "bun:test";
import { handleWriteback, type WritebackDependencies } from "../apps/worker/src/writeback-route";
import type { WorkerEnv } from "../apps/worker/src/types";
import { WritebackIntent, type WritebackIntent as WritebackIntentValue } from "../packages/contracts/src/writeback";
import type { GitHubExecutor } from "../src/github/writeback-service";
import { WritebackService } from "../src/github/writeback-service";
import { defaultSystemState } from "../src/control/state";
import { commentIntent, claimedTask, GIT_SHA, repository, SHA256 } from "./fixtures";
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

const workerEnv: WorkerEnv = {
  GITHUB_WEBHOOK_SECRET: "fixture-webhook-secret",
  CONTROL_PLANE_URL: "https://control.invalid",
  CONTROL_PLANE_INGEST_TOKEN: "control-plane-token-that-is-long-enough",
  RUNTIME_BEARER_TOKEN: "runtime-token-that-is-at-least-32-characters",
  PROVIDER_PROXY_TOKEN: "provider-token-that-is-at-least-32-characters",
  HERMES_BOT_LOGIN: "hermes[bot]",
  GITHUB_APP_ID: "123",
  GITHUB_APP_PRIVATE_KEY: "unused-in-boundary-tests",
  ENVIRONMENT: "development",
};

function runtimeWritebackRequest(intent: WritebackIntentValue): Request {
  return new Request("https://worker.invalid/runtime/writeback", {
    method: "POST",
    headers: { Authorization: `Bearer ${workerEnv.RUNTIME_BEARER_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ intent, leaseToken: intent.leaseToken }),
  });
}

function boundaryDependencies(reservation: Awaited<ReturnType<WritebackDependencies["reserve"]>>) {
  const calls = { execute: 0, complete: 0, fail: 0 };
  const dependencies: WritebackDependencies = {
    async reserve() { return reservation; },
    async execute() { calls.execute += 1; return { resultUrl: "https://github.com/desync-organization/helios/issues/7#issuecomment-42", externalId: "42" }; },
    async complete() { calls.complete += 1; },
    async fail() { calls.fail += 1; },
  };
  return { calls, dependencies };
}

function actionIntent(action: string, data: unknown, baseSha?: string): WritebackIntentValue {
  const original = commentIntent(claimedTask());
  return WritebackIntent.parse({ ...original, action, payload: { action, data }, ...(baseSha ? { baseSha } : {}) });
}

describe("credentialed write-back policy", () => {
  test("passed intent executes and persists a real result URL", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, ctx); expect(result.status).toBe("completed"); expect(result.resultUrl).toStartWith("https://github.com/"); expect(fake.calls).toBe(1); });
  test("idempotent replay returns the original URL exactly once", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const service = new WritebackService(fake); const first = await service.perform(intent, ctx); const second = await service.perform(intent, ctx); expect(second.resultUrl).toBe(first.resultUrl); expect(fake.calls).toBe(1); });
  test("global pause blocks the next mutation", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, state: { ...ctx.state, globalPaused: true } }); expect(result.status).toBe("denied"); expect(result.policyDecision.reasonCode).toBe("SYSTEM_PAUSED"); expect(fake.calls).toBe(0); });
  test("emergency mode blocks the next mutation", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, state: { ...ctx.state, emergencyMode: true } }); expect(result.policyDecision.reasonCode).toBe("SYSTEM_PAUSED"); });
  test("a paused producing agent blocks the next mutation", async () => { const fake = new FakeExecutor(); const { intent, ctx } = prepared(); const result = await new WritebackService(fake).perform(intent, { ...ctx, state: { ...ctx.state, pausedAgents: [ctx.critic.producerAgent] } }); expect(result.policyDecision.reasonCode).toBe("AGENT_PAUSED"); expect(fake.calls).toBe(0); });
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

describe("runtime write-back boundary", () => {
  test("dry-run is a successful recorded outcome and never constructs an external mutation", async () => {
    const intent = commentIntent(claimedTask());
    const { calls, dependencies } = boundaryDependencies({
      ok: false,
      replay: false,
      status: "dry_run",
      reason: "DRY_RUN",
      policyDecision: { allowed: false, reasonCode: "DRY_RUN", message: "Recorded without mutation", ruleIds: ["autonomy.dry-run"] },
    });
    const response = await handleWriteback(runtimeWritebackRequest(intent), workerEnv, dependencies);
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ writebackId: intent.writebackId, status: "dry_run", policyDecision: { reasonCode: "DRY_RUN" } });
    expect(calls).toEqual({ execute: 0, complete: 0, fail: 0 });
  });

  test("a completed idempotent replay returns the original result without another mutation", async () => {
    const intent = commentIntent(claimedTask());
    const resultUrl = "https://github.com/desync-organization/helios/issues/7#issuecomment-42";
    const { calls, dependencies } = boundaryDependencies({ ok: true, replay: true, status: "completed", resultUrl, externalId: "42" });
    const response = await handleWriteback(runtimeWritebackRequest(intent), workerEnv, dependencies);
    expect(await response.json()).toMatchObject({ status: "completed", resultUrl, replay: true });
    expect(calls).toEqual({ execute: 0, complete: 0, fail: 0 });
  });
});

describe("canonical GitHub action translations", () => {
  test("labels, milestones, duplicate closure, draft release, and private remediation PR use bounded GitHub endpoints", async () => {
    const keys = await crypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]);
    const encoded = btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.exportKey("pkcs8", keys.privateKey))));
    const pem = `-----BEGIN PRIVATE KEY-----\n${encoded.match(/.{1,64}/g)!.join("\n")}\n-----END PRIVATE KEY-----`;
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetcher = (async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      const requestBody = typeof init?.body === "string" ? JSON.parse(init.body) as Record<string, unknown> : undefined;
      calls.push({ url, method, body: requestBody });
      if (url.includes("/access_tokens")) return Response.json({ token: "installation-token" });
      if (url.endsWith("/git/ref/heads/main")) return Response.json({ object: { sha: GIT_SHA } });
      if (url.includes(`/git/commits/${GIT_SHA}`)) return Response.json({ tree: { sha: "tree-base" } });
      if (url.endsWith("/git/blobs")) return Response.json({ sha: "blob-new" });
      if (url.endsWith("/git/trees")) return Response.json({ sha: "tree-new" });
      if (url.endsWith("/git/commits")) return Response.json({ sha: "commit-new" });
      if (url.endsWith("/git/refs")) return Response.json({ ref: "refs/heads/hermes/security-fix" });
      if (url.endsWith("/pulls")) return Response.json({ html_url: "https://github.com/desync-organization/helios/pull/12", number: 12 });
      if (url.endsWith("/releases")) return Response.json({ html_url: "https://github.com/desync-organization/helios/releases/tag/v1.2.3", id: 123 });
      if (url.endsWith("/comments")) return Response.json({ html_url: "https://github.com/desync-organization/helios/issues/7#issuecomment-42", id: 42 });
      if (url.endsWith("/issues/7")) return Response.json({ html_url: "https://github.com/desync-organization/helios/issues/7", id: 7 });
      throw new Error(`Unexpected GitHub endpoint: ${method} ${url}`);
    }) as typeof fetch;
    const client = new GitHubAppClient({ appId: "123", privateKeyPem: pem }, fetcher);

    await client.execute(actionIntent("labels_set", { issueNumber: 7, labels: ["bug", "priority:high"] }), { installationId: 123, defaultBranch: "main" });
    await client.execute(actionIntent("milestone_set", { issueNumber: 7, milestoneNumber: 3 }), { installationId: 123, defaultBranch: "main" });
    await client.execute(actionIntent("duplicate_close", { issueNumber: 7, duplicateOf: 2, comment: "Verified exact duplicate.", confidence: 1 }), { installationId: 123, defaultBranch: "main" });
    await client.execute(actionIntent("release_draft", { tagName: "v1.2.3", name: "Version 1.2.3", body: "Reviewed release notes.", targetCommitish: "main", draft: true }), { installationId: 123, defaultBranch: "main" });
    await client.execute(actionIntent("security_pr", { branch: "hermes/security-fix", title: "Fix security finding", body: "Private remediation with passing tests.", files: [{ path: "src/security-fix.ts", content: "export const safe = true;", encoding: "utf-8" }], draft: true }, GIT_SHA), { installationId: 123, defaultBranch: "main", currentBaseSha: GIT_SHA });

    expect(calls.some((call) => call.url.endsWith("/issues/7") && Array.isArray(call.body?.labels))).toBeTrue();
    expect(calls.some((call) => call.url.endsWith("/issues/7") && call.body?.milestone === 3)).toBeTrue();
    expect(calls.some((call) => call.url.endsWith("/issues/7") && call.body?.state === "closed" && call.body?.state_reason === "not_planned")).toBeTrue();
    expect(calls.some((call) => call.url.endsWith("/releases") && call.body?.draft === true)).toBeTrue();
    expect(calls.some((call) => call.url.endsWith("/pulls") && call.body?.head === "hermes/security-fix" && call.body?.draft === true)).toBeTrue();
  });
});
