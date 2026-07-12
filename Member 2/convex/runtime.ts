import { internalMutation } from "./_generated/server";
import { v } from "convex/values";

export const startRun = internalMutation({
  args: { run: v.any() },
  handler: async (ctx, { run }) => {
    const existing = await ctx.db.query("runs").withIndex("by_run_id", (q) => q.eq("runId", run.runId)).unique();
    if (existing) return { duplicate: true, runId: existing.runId };
    await ctx.db.insert("runs", run);
    return { duplicate: false, runId: run.runId };
  },
});
export const appendSpan = internalMutation({
  args: { span: v.any(), feedEvent: v.any() },
  handler: async (ctx, { span, feedEvent }) => {
    const duplicate = await ctx.db.query("spans").withIndex("by_event_id", (q) => q.eq("eventId", span.eventId)).unique();
    if (duplicate) return { duplicate: true };
    const previous = await ctx.db.query("eventFeed").withIndex("by_run_sequence", (q) => q.eq("runId", span.runId)).order("desc").first();
    if (span.sequence !== (previous?.sequence ?? 0) + 1) return { duplicate: false, conflict: true, expectedSequence: (previous?.sequence ?? 0) + 1 };
    await ctx.db.insert("spans", span);
    await ctx.db.insert("eventFeed", feedEvent);
    return { duplicate: false, conflict: false };
  },
});
export const putArtifact = internalMutation({
  args: { artifact: v.any() },
  handler: async (ctx, { artifact }) => {
    const existing = await ctx.db.query("artifacts").withIndex("by_artifact_id", (q) => q.eq("artifactId", artifact.artifactId)).unique();
    if (existing) return { duplicate: true, contentHash: existing.contentHash };
    await ctx.db.insert("artifacts", artifact);
    return { duplicate: false, contentHash: artifact.contentHash };
  },
});
export const finishRun = internalMutation({
  args: { runId: v.string(), patch: v.any() },
  handler: async (ctx, { runId, patch }) => {
    const run = await ctx.db.query("runs").withIndex("by_run_id", (q) => q.eq("runId", runId)).unique();
    if (!run) return { ok: false, reason: "RUN_NOT_FOUND" };
    if (patch.status === "succeeded" && (patch.resultUrls?.length ?? 0) === 0) return { ok: false, reason: "RESULT_URL_REQUIRED" };
    await ctx.db.patch(run._id, patch);
    return { ok: true };
  },
});
