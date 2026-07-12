import { query } from "./_generated/server";
import { v } from "convex/values";

export const page = query({
  args: { runId: v.string(), cursor: v.number(), limit: v.number() },
  handler: async (ctx, args) => {
    const events = await ctx.db.query("eventFeed").withIndex("by_run_sequence", (q) => q.eq("runId", args.runId).gt("sequence", args.cursor)).take(Math.min(Math.max(args.limit, 1), 500));
    const projected = events.map(({ _id: _rawId, _creationTime: _rawCreationTime, ...event }) => event);
    return { events: projected, nextCursor: projected.at(-1)?.sequence ?? args.cursor, snapshotRequired: false };
  },
});
