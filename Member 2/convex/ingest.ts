import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

export const github = internalMutation({
  args: { webhook: v.any(), taskId: v.string(), now: v.number() },
  handler: async (ctx, { webhook, taskId, now }) => {
    const delivery = await ctx.db.query("webhookDeliveries").withIndex("by_delivery_id", (q) => q.eq("deliveryId", webhook.deliveryId)).unique();
    if (delivery) return { accepted: false, duplicate: true, taskId: delivery.taskId };
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", webhook.repo)).unique();
    if (!repository || repository.health !== "healthy") {
      await ctx.db.insert("webhookDeliveries", { deliveryId: webhook.deliveryId, event: webhook.event, action: webhook.action, repo: webhook.repo, status: "rejected", receivedAt: now, updatedAt: now });
      return { accepted: false, duplicate: false, reason: "REPOSITORY_NOT_ALLOWLISTED" };
    }
    const dedupe = await ctx.db.query("tasks").withIndex("by_repo_dedupe", (q) => q.eq("repo", webhook.repo).eq("dedupeKey", webhook.dedupeKey)).unique();
    if (dedupe) {
      await ctx.db.insert("webhookDeliveries", { deliveryId: webhook.deliveryId, event: webhook.event, action: webhook.action, repo: webhook.repo, status: "duplicate", taskId: dedupe.taskId, receivedAt: now, updatedAt: now });
      return { accepted: false, duplicate: true, taskId: dedupe.taskId };
    }
    const expiresAt = now + 24 * 60 * 60 * 1000;
    await ctx.db.insert("tasks", { taskId, source: { kind: "github", event: webhook.event, deliveryId: webhook.deliveryId, sourceUrl: webhook.sourceUrl }, mode: webhook.mode, type: webhook.type, repo: webhook.repo, payloadRedacted: webhook.payloadRedacted, status: "pending", dedupeKey: webhook.dedupeKey, requestedBy: webhook.requestedBy, consentScope: { repo: webhook.repo, allowedActions: repository.allowedActions, allowedCloudProviders: repository.visibility === "public" ? repository.allowedCloudProviders : [], allowedScanners: repository.securityAuditOptIn ? repository.allowedScanners ?? [] : [], privateCodeMayLeaveDevice: false, externalSecurityUploadAllowed: false, expiresAt, grantedBy: "repository-default", consentRef: `webhook:${webhook.deliveryId}` }, dataClassification: webhook.dataClassification, policyVersion: repository.activePolicyVersion, resultUrls: [], createdAt: now, updatedAt: now });
    await ctx.db.insert("webhookDeliveries", { deliveryId: webhook.deliveryId, event: webhook.event, action: webhook.action, repo: webhook.repo, status: "accepted", taskId, receivedAt: now, updatedAt: now });
    await ctx.db.patch(repository._id, { lastWebhookAt: now, updatedAt: now });
    return { accepted: true, duplicate: false, taskId };
  },
});

export const deadLetter = internalMutation({
  args: { record: v.any() },
  handler: async (ctx, { record }) => {
    const existing = await ctx.db.query("deadLetters").withIndex("by_delivery_id", (q) => q.eq("deliveryId", record.deliveryId)).unique();
    if (existing) { await ctx.db.patch(existing._id, { reason: record.reason, attempts: existing.attempts + 1, nextAttemptAt: Date.now() + 60_000, updatedAt: Date.now() }); return existing._id; }
    return ctx.db.insert("deadLetters", { ...record, attempts: 1, nextAttemptAt: Date.now() + 60_000, updatedAt: record.createdAt });
  },
});

export const dueDeadLetters = internalQuery({ args: { now: v.number(), limit: v.number() }, handler: (ctx, args) => ctx.db.query("deadLetters").withIndex("by_retry", (q) => q.eq("resolvedAt", undefined).lte("nextAttemptAt", args.now)).take(Math.min(args.limit, 25)) });

export const retryOne = internalMutation({
  args: { deliveryId: v.string(), taskId: v.string(), now: v.number() },
  handler: async (ctx, args) => {
    const dead = await ctx.db.query("deadLetters").withIndex("by_delivery_id", (q) => q.eq("deliveryId", args.deliveryId)).unique();
    if (!dead || dead.resolvedAt || !dead.normalized) return { ok: false, reason: "NOT_RETRYABLE" };
    const webhook = dead.normalized;
    const delivered = await ctx.db.query("webhookDeliveries").withIndex("by_delivery_id", (q) => q.eq("deliveryId", webhook.deliveryId)).unique();
    if (delivered) { await ctx.db.patch(dead._id, { resolvedAt: args.now, updatedAt: args.now }); return { ok: true, duplicate: true }; }
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", webhook.repo)).unique();
    if (!repository || repository.health !== "healthy") { await ctx.db.patch(dead._id, { attempts: dead.attempts + 1, nextAttemptAt: args.now + Math.min(3_600_000, 30_000 * 2 ** Math.min(dead.attempts, 7)), updatedAt: args.now }); return { ok: false, reason: "REPOSITORY_UNAVAILABLE" }; }
    const existing = await ctx.db.query("tasks").withIndex("by_repo_dedupe", (q) => q.eq("repo", webhook.repo).eq("dedupeKey", webhook.dedupeKey)).unique();
    const taskId = existing?.taskId ?? args.taskId;
    if (!existing) await ctx.db.insert("tasks", { taskId, source: { kind: "github", event: webhook.event, deliveryId: webhook.deliveryId, sourceUrl: webhook.sourceUrl }, mode: webhook.mode, type: webhook.type, repo: webhook.repo, payloadRedacted: webhook.payloadRedacted, status: "pending", dedupeKey: webhook.dedupeKey, requestedBy: webhook.requestedBy, consentScope: { repo: webhook.repo, allowedActions: repository.allowedActions, allowedCloudProviders: repository.visibility === "public" ? repository.allowedCloudProviders : [], allowedScanners: repository.securityAuditOptIn ? repository.allowedScanners ?? [] : [], privateCodeMayLeaveDevice: false, externalSecurityUploadAllowed: false, expiresAt: args.now + 86_400_000, grantedBy: "repository-default", consentRef: `webhook:${webhook.deliveryId}` }, dataClassification: webhook.dataClassification, policyVersion: repository.activePolicyVersion, resultUrls: [], createdAt: args.now, updatedAt: args.now });
    await ctx.db.insert("webhookDeliveries", { deliveryId: webhook.deliveryId, event: webhook.event, action: webhook.action, repo: webhook.repo, status: existing ? "duplicate" : "recovered", taskId, receivedAt: args.now, updatedAt: args.now });
    await ctx.db.patch(dead._id, { resolvedAt: args.now, updatedAt: args.now });
    return { ok: true, duplicate: Boolean(existing), taskId };
  },
});
