import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const startRun = internalMutation({
  args: { run: v.any(), leaseTokenHash: v.string(), now: v.number() },
  handler: async (ctx, { run, leaseTokenHash, now }) => {
    const task = await ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", run.taskId)).unique();
    if (!task || task.leaseTokenHash !== leaseTokenHash || !task.leaseExpiresAt || task.leaseExpiresAt <= now) return { ok: false, reason: "LOST_LEASE" };
    const existing = await ctx.db.query("runs").withIndex("by_run_id", (q) => q.eq("runId", run.runId)).unique();
    if (existing && existing.taskId !== task.taskId) return { ok: false, reason: "RUN_TASK_MISMATCH" };
    await ctx.db.patch(task._id, { activeRunId: run.runId, updatedAt: now });
    if (existing) return { ok: true, duplicate: true, runId: existing.runId };
    await ctx.db.insert("runs", run);
    return { ok: true, duplicate: false, runId: run.runId };
  },
});
export const resumeState = internalQuery({
  args: { runId: v.string() },
  handler: async (ctx, { runId }) => {
    const run = await ctx.db.query("runs").withIndex("by_run_id", (q) => q.eq("runId", runId)).unique();
    if (!run) return null;
    const previous = await ctx.db.query("eventFeed").withIndex("by_run_sequence", (q) => q.eq("runId", runId)).order("desc").first();
    return {
      runId,
      taskId: run.taskId,
      status: run.status,
      resumable: run.status === "running",
      nextSequence: (previous?.sequence ?? 0) + 1,
    };
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
export const appendEvent = internalMutation({
  args: { event: v.any() },
  handler: async (ctx, { event }) => {
    const duplicate = await ctx.db.query("eventFeed").withIndex("by_event_id", (q) => q.eq("eventId", event.eventId)).unique();
    if (duplicate) return { duplicate: true, conflict: false };
    const previous = await ctx.db.query("eventFeed").withIndex("by_run_sequence", (q) => q.eq("runId", event.runId)).order("desc").first();
    const expectedSequence = (previous?.sequence ?? 0) + 1;
    if (event.sequence !== expectedSequence) return { duplicate: false, conflict: true, expectedSequence };
    await ctx.db.insert("eventFeed", event);
    return { duplicate: false, conflict: false };
  },
});
export const appendCompletion = internalMutation({
  args: { taskId: v.string(), runId: v.string(), resultUrl: v.string(), now: v.number() },
  handler: async (ctx, args) => {
    const eventId = `completion:${args.runId}`;
    const duplicate = await ctx.db.query("eventFeed").withIndex("by_event_id", (q) => q.eq("eventId", eventId)).unique();
    if (duplicate) return { duplicate: true };
    const previous = await ctx.db.query("eventFeed").withIndex("by_run_sequence", (q) => q.eq("runId", args.runId)).order("desc").first();
    await ctx.db.insert("eventFeed", { eventId, runId: args.runId, taskId: args.taskId, sequence: (previous?.sequence ?? 0) + 1, kind: "writeback_completed", label: "live", projectionRedacted: { type: "writeback_completed", source: "control-plane", resultUrl: args.resultUrl, payload: { text: "GitHub write-back completed" } }, createdAt: args.now });
    return { duplicate: false };
  },
});
export const putSpan = internalMutation({
  args: { span: v.any() },
  handler: async (ctx, { span }) => {
    const existing = await ctx.db.query("spans").withIndex("by_span_id", (q) => q.eq("spanId", span.spanId)).unique();
    if (existing) return { duplicate: true };
    await ctx.db.insert("spans", span);
    return { duplicate: false };
  },
});
export const putArtifact = internalMutation({
  args: { artifact: v.any() },
  handler: async (ctx, { artifact }) => {
    const existing = await ctx.db.query("artifacts").withIndex("by_artifact_id", (q) => q.eq("artifactId", artifact.artifactId)).unique();
    if (existing) return { duplicate: true, conflict: existing.contentHash !== artifact.contentHash, contentHash: existing.contentHash };
    await ctx.db.insert("artifacts", artifact);
    return { duplicate: false, conflict: false, contentHash: artifact.contentHash };
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

export const finalizeRun = internalMutation({
  args: {
    taskId: v.string(),
    ownerId: v.string(),
    leaseTokenHash: v.string(),
    taskStatus: v.string(),
    resultUrls: v.array(v.string()),
    error: v.optional(v.any()),
    runId: v.string(),
    runPatch: v.any(),
    now: v.number(),
  },
  handler: async (ctx, args) => {
    const task = await ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", args.taskId)).unique();
    const run = await ctx.db.query("runs").withIndex("by_run_id", (q) => q.eq("runId", args.runId)).unique();
    if (!task || !run || run.taskId !== args.taskId) return { ok: false, reason: "RUN_SCOPE_MISMATCH" };
    if (task.status === args.taskStatus && run.status === args.runPatch.status) return { ok: true, duplicate: true };
    if (task.leaseOwnerId !== args.ownerId || task.leaseTokenHash !== args.leaseTokenHash || !task.leaseExpiresAt || task.leaseExpiresAt <= args.now) return { ok: false, reason: "LOST_LEASE" };
    if (args.taskStatus === "done" && (args.resultUrls.length === 0 || args.resultUrls.some((url) => !url.startsWith("https://")))) return { ok: false, reason: "RESULT_URL_REQUIRED" };
    if (args.runPatch.status === "succeeded" && args.resultUrls.length === 0) return { ok: false, reason: "RESULT_URL_REQUIRED" };
    await ctx.db.patch(task._id, {
      status: args.taskStatus,
      resultUrls: args.resultUrls,
      error: args.error,
      activeRunId: undefined,
      leaseOwnerId: undefined,
      leaseTokenHash: undefined,
      leaseAcquiredAt: undefined,
      leaseHeartbeatAt: undefined,
      leaseExpiresAt: undefined,
      updatedAt: args.now,
    });
    await ctx.db.patch(run._id, args.runPatch);
    if (args.taskStatus === "done" && args.resultUrls[0]) {
      const eventId = `completion:${args.runId}`;
      const duplicate = await ctx.db.query("eventFeed").withIndex("by_event_id", (q) => q.eq("eventId", eventId)).unique();
      if (!duplicate) {
        const previous = await ctx.db.query("eventFeed").withIndex("by_run_sequence", (q) => q.eq("runId", args.runId)).order("desc").first();
        await ctx.db.insert("eventFeed", { eventId, runId: args.runId, taskId: args.taskId, sequence: (previous?.sequence ?? 0) + 1, kind: "writeback_completed", label: "live", projectionRedacted: { type: "writeback_completed", source: "control-plane", resultUrl: args.resultUrls[0], payload: { text: "GitHub write-back completed" } }, createdAt: args.now });
      }
    }
    return { ok: true, duplicate: false };
  },
});
