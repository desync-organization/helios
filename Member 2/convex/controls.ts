import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const get = internalQuery({ args: {}, handler: async (ctx) => ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique() });
export const update = internalMutation({
  args: { patch: v.any(), now: v.number() },
  handler: async (ctx, { patch, now }) => {
    const existing = await ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    const current = existing ? { globalPaused: existing.globalPaused, emergencyMode: existing.emergencyMode, pausedAgents: existing.pausedAgents, writebackMode: existing.writebackMode, securityScanMode: existing.securityScanMode, currentAgentTag: existing.currentAgentTag, currentAdapterPointers: existing.currentAdapterPointers } : {};
    const next = { globalPaused: false, emergencyMode: false, pausedAgents: [], writebackMode: "dry-run", securityScanMode: "read-only", currentAgentTag: "agents-v1", currentAdapterPointers: {}, ...current, ...patch, key: "global", updatedAt: now };
    if (existing) { await ctx.db.patch(existing._id, next); return existing._id; }
    return ctx.db.insert("systemState", next);
  },
});
