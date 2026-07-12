import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const register = internalMutation({ args: { adapter: v.any() }, handler: async (ctx, { adapter }) => { const existing = await ctx.db.query("adapters").withIndex("by_adapter_id", (q) => q.eq("adapterId", adapter.adapterId)).unique(); if (existing) return { duplicate: true }; await ctx.db.insert("adapters", adapter); return { duplicate: false }; } });
export const activate = internalMutation({
  args: { adapterId: v.string(), approvedBy: v.string(), now: v.number() },
  handler: async (ctx, args) => {
    const adapter = await ctx.db.query("adapters").withIndex("by_adapter_id", (q) => q.eq("adapterId", args.adapterId)).unique();
    if (!adapter || !adapter.tenRunBenchmarkPassed || adapter.stableGauntletRuns.length !== 3 || !adapter.safetySubgroupsPassed || !adapter.qualityApprovedBy || !adapter.compatibilityApprovedBy) return { ok: false, reason: "PROMOTION_GATES_FAILED" };
    const state = await ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    if (!state) return { ok: false, reason: "SYSTEM_STATE_MISSING" };
    const pointers = { ...(state.currentAdapterPointers as Record<string, string>) };
    const predecessorByRole: Record<string, string | undefined> = {};
    for (const role of adapter.activeRoles) { predecessorByRole[role] = pointers[role]; pointers[role] = adapter.adapterId; }
    await ctx.db.patch(state._id, { currentAdapterPointers: pointers, updatedAt: args.now });
    await ctx.db.patch(adapter._id, { status: "active", updatedAt: args.now });
    await ctx.db.insert("adapterPromotions", { promotionId: `activate:${adapter.adapterId}:${args.now}`, adapterId: adapter.adapterId, action: "activate", roles: adapter.activeRoles, predecessorByRole, approvedBy: args.approvedBy, reason: "All promotion gates passed", createdAt: args.now });
    return { ok: true, pointers };
  },
});
export const rollback = internalMutation({
  args: { adapterId: v.string(), approvedBy: v.string(), reason: v.string(), now: v.number() },
  handler: async (ctx, args) => {
    const promotions = await ctx.db.query("adapterPromotions").withIndex("by_adapter_created", (q) => q.eq("adapterId", args.adapterId)).order("desc").collect();
    const activation = promotions.find((promotion) => promotion.action === "activate");
    const state = await ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    if (!activation || !state) return { ok: false, reason: "ACTIVATION_NOT_FOUND" };
    const pointers = { ...(state.currentAdapterPointers as Record<string, string>) };
    for (const role of activation.roles) { const predecessor = activation.predecessorByRole[role]; if (predecessor) pointers[role] = predecessor; else delete pointers[role]; }
    await ctx.db.patch(state._id, { currentAdapterPointers: pointers, updatedAt: args.now });
    const adapter = await ctx.db.query("adapters").withIndex("by_adapter_id", (q) => q.eq("adapterId", args.adapterId)).unique();
    if (adapter) await ctx.db.patch(adapter._id, { status: "rolled_back", updatedAt: args.now });
    await ctx.db.insert("adapterPromotions", { promotionId: `rollback:${args.adapterId}:${args.now}`, adapterId: args.adapterId, action: "rollback", roles: activation.roles, predecessorByRole: activation.predecessorByRole, approvedBy: args.approvedBy, reason: args.reason, createdAt: args.now });
    return { ok: true, pointers };
  },
});
export const activePointers = internalQuery({ args: {}, handler: async (ctx) => (await ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique())?.currentAdapterPointers ?? {} });
