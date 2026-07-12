import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const upsert = internalMutation({
  args: { repository: v.any() },
  handler: async (ctx, { repository }) => {
    const existing = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", repository.repo)).unique();
    if (existing) { await ctx.db.replace(existing._id, repository); return existing._id; }
    return ctx.db.insert("repositories", repository);
  },
});
export const getPrivate = internalQuery({ args: { repo: v.string() }, handler: (ctx, args) => ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", args.repo)).unique() });
export const getRedacted = internalQuery({
  args: { repo: v.string() },
  handler: async (ctx, args) => {
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", args.repo)).unique();
    if (!repository) return null;
    const { _id: _rawId, _creationTime: _rawCreationTime, installationId: _installationId, githubRepositoryId: _githubRepositoryId, ...redacted } = repository;
    return redacted;
  },
});
