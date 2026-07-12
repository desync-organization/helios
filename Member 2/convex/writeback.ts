import { internalMutation } from "./_generated/server";
import { v } from "convex/values";

const PR_ACTIONS = new Set(["branch_and_pr", "build_branch_and_pr", "security_pr", "policy_commit", "eval_case_commit"]);
const SECRET_SHAPES = [/gh[pousr]_[A-Za-z0-9]{20,}/i, /github_pat_[A-Za-z0-9_]{20,}/i, /-----BEGIN .*PRIVATE KEY-----/i, /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/];
function isProtectedPath(path: string, patterns: string[]): boolean {
  return patterns.some((pattern) => {
    const normalized = pattern.replace(/^\//, "");
    if (normalized.endsWith("/**")) return path === normalized.slice(0, -3) || path.startsWith(normalized.slice(0, -2));
    if (normalized.endsWith("*")) return path.startsWith(normalized.slice(0, -1));
    return path === normalized || path.startsWith(`${normalized}/`);
  });
}

export const reserve = internalMutation({
  args: { intent: v.any(), leaseTokenHash: v.string(), now: v.number() },
  handler: async (ctx, { intent, leaseTokenHash, now }) => {
    const replay = await ctx.db.query("writebackActions").withIndex("by_repo_idempotency", (q) => q.eq("repo", intent.repo).eq("idempotencyKey", intent.idempotencyKey)).unique();
    if (replay) return { ok: replay.status === "completed", replay: true, status: replay.status, resultUrl: replay.resultUrl, reason: replay.status === "pending" ? "IN_PROGRESS" : undefined };
    const [task, repository, state, artifact, critic] = await Promise.all([
      ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", intent.taskId)).unique(),
      ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", intent.repo)).unique(),
      ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique(),
      ctx.db.query("artifacts").withIndex("by_artifact_id", (q) => q.eq("artifactId", intent.artifactId)).unique(),
      ctx.db.query("artifacts").withIndex("by_artifact_id", (q) => q.eq("artifactId", intent.criticArtifactId)).unique(),
    ]);
    let reason: string | undefined;
    let criticContent: any = null;
    try { criticContent = critic?.contentRedacted ? JSON.parse(critic.contentRedacted) : null; } catch { criticContent = null; }
    const files = PR_ACTIONS.has(intent.action) && Array.isArray(intent.payload?.data?.files) ? intent.payload.data.files : [];
    const paths = files.map((file: any) => String(file.path ?? ""));
    const patchBytes = files.reduce((total: number, file: any) => total + String(file.content ?? "").length, 0);
    if (!task || !repository || !state || !artifact || !critic) reason = "CONTEXT_MISSING";
    else if (task.repo !== intent.repo || repository.repo !== intent.repo) reason = "REPOSITORY_MISMATCH";
    else if (!task.leaseExpiresAt || task.leaseExpiresAt <= now || task.leaseTokenHash !== leaseTokenHash) reason = "LOST_LEASE";
    else if (state.globalPaused || state.emergencyMode) reason = "SYSTEM_PAUSED";
    else if (state.writebackMode === "dry-run") reason = "DRY_RUN";
    else if (state.writebackMode === "pr-only" && !PR_ACTIONS.has(intent.action)) reason = "PR_ONLY";
    else if (!repository.writebackOptIn || repository.health !== "healthy" || !repository.allowedActions.includes(intent.action) || !task.consentScope.allowedActions.includes(intent.action) || task.consentScope.expiresAt <= now) reason = "ACTION_NOT_ALLOWED";
    else if (artifact.contentHash !== intent.artifactHash) reason = "ARTIFACT_HASH_MISMATCH";
    else if (critic.type !== "critic_verdict" || criticContent?.verdict !== "pass" || criticContent?.reviewedArtifactId !== intent.artifactId || criticContent?.reviewedContentHash !== intent.artifactHash || criticContent?.producerAgent === criticContent?.criticAgent) reason = "CRITIC_MISMATCH";
    else if (!intent.testsPassed || !intent.securityChecksPassed || !intent.requiredChecksPassed || intent.breakingChange) reason = "QUALITY_GATES_FAILED";
    else if (task.mode === "security_audit" && state.securityScanMode === "read-only") reason = "SECURITY_READ_ONLY";
    else if (intent.action === "security_issue_draft") reason = "PUBLIC_SECURITY_DISCLOSURE_DISABLED";
    else if (paths.length > repository.sizeLimits.maxFiles || patchBytes > repository.sizeLimits.maxPatchBytes) reason = "PATCH_TOO_LARGE";
    else if (paths.some((path: string) => isProtectedPath(path, repository.protectedPaths))) reason = "PROTECTED_PATH";
    else if (files.some((file: any) => SECRET_SHAPES.some((pattern) => pattern.test(String(file.content ?? ""))))) reason = "SECRET_IN_PATCH";
    else if (intent.action === "pr_merge" && repository.requiredChecks.length === 0) reason = "MERGE_POLICY_INCOMPLETE";
    const status = reason ? (reason === "DRY_RUN" ? "dry_run" : "denied") : "pending";
    await ctx.db.insert("writebackActions", { writebackId: intent.writebackId, taskId: intent.taskId, runId: intent.runId, repo: intent.repo, action: intent.action, idempotencyKey: intent.idempotencyKey, artifactId: intent.artifactId, artifactHash: intent.artifactHash, criticArtifactId: intent.criticArtifactId, policyDecision: { allowed: !reason, reasonCode: reason ?? "ALLOWED" }, status, createdAt: now, updatedAt: now });
    return reason ? { ok: false, replay: false, status, reason } : { ok: true, replay: false, status, installationId: repository!.installationId, defaultBranch: repository!.defaultBranch };
  },
});
export const complete = internalMutation({
  args: { writebackId: v.string(), resultUrl: v.string(), externalId: v.string(), now: v.number() },
  handler: async (ctx, args) => {
    if (!args.resultUrl.startsWith("https://")) return { ok: false, reason: "INVALID_RESULT_URL" };
    const action = await ctx.db.query("writebackActions").withIndex("by_writeback_id", (q) => q.eq("writebackId", args.writebackId)).unique();
    if (!action || action.status !== "pending") return { ok: false, reason: "NOT_PENDING" };
    await ctx.db.patch(action._id, { status: "completed", resultUrl: args.resultUrl, externalId: args.externalId, updatedAt: args.now });
    return { ok: true };
  },
});
export const fail = internalMutation({ args: { writebackId: v.string(), error: v.any(), now: v.number() }, handler: async (ctx, args) => { const action = await ctx.db.query("writebackActions").withIndex("by_writeback_id", (q) => q.eq("writebackId", args.writebackId)).unique(); if (!action || action.status !== "pending") return { ok: false }; await ctx.db.patch(action._id, { status: "failed", error: args.error, updatedAt: args.now }); return { ok: true }; } });
