import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const activateAfterGitCommit = internalMutation({
  args: { policy: v.any(), gitCommitSucceeded: v.boolean(), now: v.number() },
  handler: async (ctx, args) => {
    if (!args.gitCommitSucceeded || !/^[a-f0-9]{40}$/i.test(args.policy.gitCommitSha)) return { ok: false, reason: "AUDITED_GIT_COMMIT_REQUIRED" };
    const active = await ctx.db.query("policies").withIndex("by_repo_active", (q) => q.eq("repo", args.policy.repo).eq("active", true)).collect();
    for (const policy of active.filter((item) => item.name === args.policy.name)) await ctx.db.patch(policy._id, { active: false });
    await ctx.db.insert("policies", { ...args.policy, active: true, activatedAt: args.now, createdAt: args.now });
    return { ok: true };
  },
});
export const active = internalQuery({ args: { repo: v.string() }, handler: (ctx, args) => ctx.db.query("policies").withIndex("by_repo_active", (q) => q.eq("repo", args.repo).eq("active", true)).collect() });
