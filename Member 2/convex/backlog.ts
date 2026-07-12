import { internalMutation } from "./_generated/server";
import { v } from "convex/values";

export const approve = internalMutation({
  args: { batch: v.any() },
  handler: async (ctx, { batch }) => {
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", batch.repo)).unique();
    const prefix = `https://github.com/${batch.repo}/issues/`;
    if (!repository || !batch.issueUrls.length || batch.issueUrls.some((url: string) => !url.startsWith(prefix) || !/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/issues\/\d+$/.test(url))) return { ok: false, reason: "ALLOWLISTED_EXISTING_ISSUE_URLS_REQUIRED" };
    await ctx.db.insert("approvedBacklogBatches", batch);
    return { ok: true };
  },
});
