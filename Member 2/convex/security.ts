import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

const SECRET_SHAPES = [/gh[pousr]_[A-Za-z0-9]{20,}/i, /github_pat_[A-Za-z0-9_]{20,}/i, /-----BEGIN .*PRIVATE KEY-----/i, /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/];

function persistedFinding(finding: any, now: number): Record<string, unknown> {
  return {
    findingId: finding.findingId,
    repo: finding.repo,
    fingerprint: finding.fingerprint,
    scanner: finding.scanner,
    scannerVersion: finding.scannerVersion,
    ruleId: finding.ruleId,
    category: finding.category,
    severity: finding.severity,
    confidence: finding.confidence,
    advisoryUrls: finding.advisoryUrls ?? [],
    commitSha: finding.commitSha,
    evidenceRedacted: finding.evidenceRedacted,
    exploitability: finding.exploitability,
    reachability: finding.reachability,
    recommendedFix: finding.recommendedFix,
    status: finding.status,
    restricted: true,
    createdAt: now,
    updatedAt: now,
    ...(finding.cwe ? { cwe: finding.cwe } : {}),
    ...(finding.cve ? { cve: finding.cve } : {}),
    ...(finding.advisoryRetrievedAt ? { advisoryRetrievedAt: finding.advisoryRetrievedAt } : {}),
    ...(finding.path ? { path: finding.path } : {}),
    ...(finding.startLine ? { startLine: finding.startLine } : {}),
    ...(finding.endLine ? { endLine: finding.endLine } : {}),
    ...(finding.falsePositiveReason ? { falsePositiveReason: finding.falsePositiveReason } : {}),
  };
}

export const upsertFinding = internalMutation({
  args: { finding: v.any(), now: v.number() },
  handler: async (ctx, { finding, now }) => {
    const serialized = JSON.stringify(finding);
    if (SECRET_SHAPES.some((pattern) => pattern.test(serialized))) return { ok: false, reason: "RAW_SECRET_REJECTED" };
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", finding.repo)).unique();
    if (!repository?.securityAuditOptIn) return { ok: false, reason: "SECURITY_AUDIT_NOT_CONSENTED" };
    for (const artifactId of finding.artifactIds ?? []) {
      const artifact = await ctx.db.query("artifacts").withIndex("by_artifact_id", (q) => q.eq("artifactId", artifactId)).unique();
      if (!artifact || artifact.taskId !== finding.taskId) return { ok: false, reason: "ARTIFACT_SCOPE_MISMATCH" };
    }
    const existing = await ctx.db.query("securityFindings").withIndex("by_repo_fingerprint", (q) => q.eq("repo", finding.repo).eq("fingerprint", finding.fingerprint)).unique();
    const stored = persistedFinding(finding, now);
    if (existing) { const patch = { ...stored }; delete patch.createdAt; await ctx.db.patch(existing._id, patch); return { ok: true, duplicate: true, findingId: existing.findingId }; }
    await ctx.db.insert("securityFindings", stored as any);
    await ctx.db.insert("reviewItems", { reviewItemId: `review:${finding.findingId}`, repo: finding.repo, taskId: finding.taskId ?? "security-scan", kind: "security_finding", restricted: true, status: "pending", reasonRedacted: `${finding.severity} ${finding.category} finding requires private review`, artifactIds: finding.artifactIds ?? [], createdAt: now, updatedAt: now });
    return { ok: true, duplicate: false, findingId: finding.findingId };
  },
});

export const byRepository = internalQuery({ args: { repo: v.string(), status: v.optional(v.string()) }, handler: async (ctx, args) => args.status ? ctx.db.query("securityFindings").withIndex("by_repo_status", (q) => q.eq("repo", args.repo).eq("status", args.status!)).collect() : ctx.db.query("securityFindings").withIndex("by_repo_status", (q) => q.eq("repo", args.repo)).collect() });
