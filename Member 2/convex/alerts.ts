import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const emit = internalMutation({ args: { event: v.any() }, handler: async (ctx, { event }) => { const existing = await ctx.db.query("alertEvents").withIndex("by_alert_id", (q) => q.eq("alertId", event.alertId)).unique(); if (existing) return { duplicate: true }; await ctx.db.insert("alertEvents", event); return { duplicate: false }; } });
export const recent = internalQuery({ args: { kind: v.string(), limit: v.number() }, handler: (ctx, args) => ctx.db.query("alertEvents").withIndex("by_kind_created", (q) => q.eq("kind", args.kind)).order("desc").take(Math.min(args.limit, 200)) });
export const acknowledge = internalMutation({ args: { alertId: v.string(), now: v.number() }, handler: async (ctx, args) => { const event = await ctx.db.query("alertEvents").withIndex("by_alert_id", (q) => q.eq("alertId", args.alertId)).unique(); if (!event) return { ok: false }; await ctx.db.patch(event._id, { acknowledgedAt: args.now }); return { ok: true }; } });
