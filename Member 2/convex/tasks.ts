import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

const LEASE_MIN_MS = 5_000;
const LEASE_MAX_MS = 300_000;

export const enqueue = internalMutation({
  args: { task: v.any() },
  handler: async (ctx, { task }) => {
    const existing = await ctx.db.query("tasks").withIndex("by_repo_dedupe", (q) => q.eq("repo", task.repo).eq("dedupeKey", task.dedupeKey)).unique();
    if (existing) return { taskId: existing.taskId, duplicate: true };
    await ctx.db.insert("tasks", { ...task, payloadRedacted: task.payloadRedacted ?? task.payload, resultUrls: task.resultUrls ?? [] });
    return { taskId: task.taskId, duplicate: false };
  },
});

export const claim = internalMutation({
  args: { ownerId: v.string(), leaseTokenHash: v.string(), leaseMs: v.number(), now: v.number() },
  handler: async (ctx, args) => {
    const pending = await ctx.db.query("tasks").withIndex("by_status_created", (q) => q.eq("status", "pending")).first();
    const expiredClaimed = pending ? null : await ctx.db.query("tasks").withIndex("by_status_created", (q) => q.eq("status", "claimed")).filter((q) => q.lte(q.field("leaseExpiresAt"), args.now)).first();
    const expiredRunning = pending || expiredClaimed ? null : await ctx.db.query("tasks").withIndex("by_status_created", (q) => q.eq("status", "running")).filter((q) => q.lte(q.field("leaseExpiresAt"), args.now)).first();
    const task = pending ?? expiredClaimed ?? expiredRunning;
    if (!task) return null;
    const leaseMs = Math.min(Math.max(args.leaseMs, LEASE_MIN_MS), LEASE_MAX_MS);
    await ctx.db.patch(task._id, { status: "claimed", leaseOwnerId: args.ownerId, leaseTokenHash: args.leaseTokenHash, leaseAcquiredAt: args.now, leaseHeartbeatAt: args.now, leaseExpiresAt: args.now + leaseMs, updatedAt: args.now });
    return { ...task, status: "claimed", leaseOwnerId: args.ownerId, leaseExpiresAt: args.now + leaseMs };
  },
});

export const heartbeat = internalMutation({
  args: { taskId: v.string(), ownerId: v.string(), leaseTokenHash: v.string(), extensionMs: v.number(), now: v.number() },
  handler: async (ctx, args) => {
    const task = await ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", args.taskId)).unique();
    if (!task || task.leaseOwnerId !== args.ownerId || task.leaseTokenHash !== args.leaseTokenHash || !task.leaseExpiresAt || task.leaseExpiresAt <= args.now) return { ok: false, reason: "LOST_LEASE" };
    const extension = Math.min(Math.max(args.extensionMs, LEASE_MIN_MS), LEASE_MAX_MS);
    await ctx.db.patch(task._id, { status: "running", leaseHeartbeatAt: args.now, leaseExpiresAt: args.now + extension, updatedAt: args.now });
    return { ok: true, expiresAt: args.now + extension };
  },
});

export const finish = internalMutation({
  args: { taskId: v.string(), ownerId: v.string(), leaseTokenHash: v.string(), status: v.string(), resultUrls: v.array(v.string()), error: v.optional(v.any()), now: v.number() },
  handler: async (ctx, args) => {
    const task = await ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", args.taskId)).unique();
    if (!task || task.leaseOwnerId !== args.ownerId || task.leaseTokenHash !== args.leaseTokenHash || !task.leaseExpiresAt || task.leaseExpiresAt <= args.now) return { ok: false, reason: "LOST_LEASE" };
    if (args.status === "done" && (args.resultUrls.length === 0 || args.resultUrls.some((url) => !url.startsWith("https://")))) return { ok: false, reason: "RESULT_URL_REQUIRED" };
    await ctx.db.patch(task._id, { status: args.status, resultUrls: args.resultUrls, error: args.error, leaseOwnerId: undefined, leaseTokenHash: undefined, leaseAcquiredAt: undefined, leaseHeartbeatAt: undefined, leaseExpiresAt: undefined, updatedAt: args.now });
    return { ok: true };
  },
});

export const getByTaskId = internalQuery({ args: { taskId: v.string() }, handler: (ctx, args) => ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", args.taskId)).unique() });
