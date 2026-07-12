import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

const SECRET_SHAPES = [/gh[pousr]_[A-Za-z0-9]{20,}/i, /github_pat_[A-Za-z0-9_]{20,}/i, /-----BEGIN .*PRIVATE KEY-----/i, /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/];

export const upsertFinding = internalMutation({
  args: { finding: v.any(), now: v.number() },
  handler: async (ctx, { finding, now }) => {
    const serialized = JSON.stringify(finding);
    if (SECRET_SHAPES.some((pattern) => pattern.test(serialized))) return { ok: false, reason: "RAW_SECRET_REJECTED" };
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", finding.repo)).unique();
    if (!repository?.securityAuditOptIn) return { ok: false, reason: "SECURITY_AUDIT_NOT_CONSENTED" };
    const existing = await ctx.db.query("securityFindings").withIndex("by_repo_fingerprint", (q) => q.eq("repo", finding.repo).eq("fingerprint", finding.fingerprint)).unique();
    if (existing) { await ctx.db.patch(existing._id, { ...finding, updatedAt: now }); return { ok: true, duplicate: true, findingId: existing.findingId }; }
    await ctx.db.insert("securityFindings", { ...finding, restricted: true, createdAt: now, updatedAt: now });
    await ctx.db.insert("reviewItems", { reviewItemId: `review:${finding.findingId}`, repo: finding.repo, taskId: finding.taskId ?? "security-scan", kind: "security_finding", restricted: true, status: "pending", reasonRedacted: `${finding.severity} ${finding.category} finding requires private review`, artifactIds: finding.artifactIds ?? [], createdAt: now, updatedAt: now });
    return { ok: true, duplicate: false, findingId: finding.findingId };
  },
});

export const byRepository = internalQuery({ args: { repo: v.string(), status: v.optional(v.string()) }, handler: async (ctx, args) => args.status ? ctx.db.query("securityFindings").withIndex("by_repo_status", (q) => q.eq("repo", args.repo).eq("status", args.status!)).collect() : ctx.db.query("securityFindings").withIndex("by_repo_status", (q) => q.eq("repo", args.repo)).collect() });
