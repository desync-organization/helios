import { internalMutation } from "./_generated/server";
import { v } from "convex/values";

export const captureCandidate = internalMutation({
  args: { candidate: v.any() },
  handler: async (ctx, { candidate }) => {
    const existing = await ctx.db.query("evalCases").withIndex("by_eval_case_id", (q) => q.eq("evalCaseId", candidate.evalCaseId)).unique();
    if (existing) return { duplicate: true };
    await ctx.db.insert("evalCases", { ...candidate, status: "pending-review", updatedAt: candidate.createdAt });
    return { duplicate: false };
  },
});
export const recordRun = internalMutation({ args: { run: v.any() }, handler: async (ctx, { run }) => { const existing = await ctx.db.query("evalRuns").withIndex("by_eval_run_id", (q) => q.eq("evalRunId", run.evalRunId)).unique(); if (existing) return { duplicate: true }; await ctx.db.insert("evalRuns", run); return { duplicate: false }; } });
