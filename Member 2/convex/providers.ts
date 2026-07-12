import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const authorize = internalQuery({
  args: { taskId: v.string(), repo: v.string(), purpose: v.string(), requestedProvider: v.optional(v.string()), now: v.number() },
  handler: async (ctx, args) => {
    const task = await ctx.db.query("tasks").withIndex("by_task_id", (q) => q.eq("taskId", args.taskId)).unique();
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", args.repo)).unique();
    if (!task || !repository || task.repo !== args.repo || task.consentScope?.repo !== args.repo || task.consentScope?.expiresAt <= args.now) return { allowed: false, reason: "CONSENT_MISSING" };
    const providers = task.consentScope.allowedCloudProviders.filter((provider: string) => repository.allowedCloudProviders.includes(provider));
    if (repository.visibility !== "public" && !task.consentScope.privateCodeMayLeaveDevice) return { allowed: false, reason: "PRIVATE_LOCAL_ONLY" };
    if (args.requestedProvider && !providers.includes(args.requestedProvider)) return { allowed: false, reason: "PROVIDER_NOT_ALLOWED" };
    if (args.purpose === "vulnerability_intelligence" && !task.consentScope.externalSecurityUploadAllowed) return { allowed: false, reason: "SECURITY_EGRESS_NOT_ALLOWED" };
    return { allowed: true, providers, consentRef: task.consentScope.consentRef, classification: task.dataClassification };
  },
});

export const record = internalMutation({
  args: { call: v.any() },
  handler: async (ctx, { call }) => {
    const existing = await ctx.db.query("providerCalls").withIndex("by_request_id", (q) => q.eq("requestId", call.requestId)).unique();
    if (existing) return { duplicate: true, providerCallId: existing.providerCallId };
    await ctx.db.insert("providerCalls", call);
    return { duplicate: false, providerCallId: call.providerCallId };
  },
});
