import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const upsertEntity = internalMutation({
  args: { entity: v.any() },
  handler: async (ctx, { entity }) => {
    const existing = await ctx.db.query("entities").withIndex("by_repo_kind_key", (q) => q.eq("repo", entity.repo).eq("kind", entity.kind).eq("externalKey", entity.externalKey)).unique();
    if (existing) { await ctx.db.patch(existing._id, entity); return existing._id; }
    return ctx.db.insert("entities", entity);
  },
});
export const pack = internalQuery({ args: { repo: v.string(), now: v.number(), limit: v.number() }, handler: (ctx, args) => ctx.db.query("entities").withIndex("by_repo_layer", (q) => q.eq("repo", args.repo)).filter((q) => q.gt(q.field("expiresAt"), args.now)).take(Math.min(args.limit, 100)) });
export const deleteExpired = internalMutation({
  args: { now: v.number(), limit: v.number() },
  handler: async (ctx, args) => {
    const expired = await ctx.db.query("entities").withIndex("by_expiry", (q) => q.lt("expiresAt", args.now)).take(Math.min(args.limit, 500));
    for (const entity of expired) await ctx.db.delete(entity._id);
    return { deleted: expired.length };
  },
});
