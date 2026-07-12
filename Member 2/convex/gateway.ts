import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

const GITHUB_URL = /^https:\/\/github\.com\/([A-Za-z0-9_.-]{1,100})\/([A-Za-z0-9_.-]{1,100})(?:\/(issues|pull)\/(\d+))?\/?(?:[?#].*)?$/;

export const createTaskDraft = internalMutation({
  args: { draft: v.any(), idempotencyKey: v.string(), taskId: v.string(), now: v.number() },
  handler: async (ctx, args) => {
    const prompt = String(args.draft.prompt ?? "").trim();
    const match = prompt.match(GITHUB_URL) ?? prompt.match(/https:\/\/github\.com\/([A-Za-z0-9_.-]{1,100})\/([A-Za-z0-9_.-]{1,100})(?:\/(issues|pull)\/(\d+))/);
    if (!match) return { ok: false, reason: "GITHUB_URL_REQUIRED" };
    const repo = `${match[1]}/${match[2]}`;
    const repository = await ctx.db.query("repositories").withIndex("by_repo", (q) => q.eq("repo", repo)).unique();
    if (!repository || repository.health !== "healthy") return { ok: false, reason: "REPOSITORY_NOT_ALLOWLISTED" };
    const existing = await ctx.db.query("tasks").withIndex("by_repo_dedupe", (q) => q.eq("repo", repo).eq("dedupeKey", `operator:${args.idempotencyKey}`)).unique();
    if (existing) return { ok: true, duplicate: true, taskId: existing.taskId };
    const itemKind = match[3];
    const itemNumber = match[4] ? Number(match[4]) : undefined;
    const sourceUrl = match[0];
    const expiresAt = args.now + 24 * 60 * 60 * 1000;
    await ctx.db.insert("tasks", {
      taskId: args.taskId,
      source: { kind: "operator", promptId: args.idempotencyKey, sourceUrl },
      mode: "maintain",
      type: itemKind === "pull" ? "review" : itemKind === "issues" ? "respond" : "intake",
      repo,
      payloadRedacted: JSON.stringify({ prompt, sourceUrl, issue: itemKind === "issues" ? { number: itemNumber, html_url: sourceUrl } : undefined, pull_request: itemKind === "pull" ? { number: itemNumber, html_url: sourceUrl } : undefined }),
      status: "pending",
      dedupeKey: `operator:${args.idempotencyKey}`,
      requestedBy: "operator",
      consentScope: { repo, allowedActions: repository.allowedActions, allowedCloudProviders: repository.visibility === "public" ? repository.allowedCloudProviders : [], privateCodeMayLeaveDevice: false, externalSecurityUploadAllowed: false, expiresAt, grantedBy: "operator", consentRef: `operator:${args.idempotencyKey}` },
      dataClassification: repository.visibility === "public" ? "public" : "private",
      policyVersion: repository.activePolicyVersion,
      resultUrls: [],
      createdAt: args.now,
      updatedAt: args.now,
    });
    return { ok: true, duplicate: false, taskId: args.taskId };
  },
});

export const eventsAfter = internalQuery({
  args: { after: v.optional(v.string()), limit: v.number() },
  handler: async (ctx, args) => {
    const after = args.after ? await ctx.db.query("eventFeed").withIndex("by_event_id", (q) => q.eq("eventId", args.after!)).unique() : null;
    const values = await ctx.db.query("eventFeed").withIndex("by_created", (q) => after ? q.gte("createdAt", after.createdAt) : q).order("asc").take(Math.min(Math.max(args.limit, 1), 500));
    return values
      .filter((event) => !after || event.createdAt > after.createdAt || event.eventId !== after.eventId)
      .map(({ _id: _rawId, _creationTime: _rawCreationTime, ...event }) => event);
  },
});

export const statuses = internalQuery({
  args: {},
  handler: async (ctx) => {
    const active = await ctx.db.query("tasks").withIndex("by_status_created", (q) => q.eq("status", "running")).first()
      ?? await ctx.db.query("tasks").withIndex("by_status_created", (q) => q.eq("status", "claimed")).first();
    return [{
      wrapperId: "helios-runtime",
      wrapperType: "runtime",
      status: active ? "WORKING" : "IDLE",
      lastSeen: new Date(active?.updatedAt ?? Date.now()).toISOString(),
    }];
  },
});
