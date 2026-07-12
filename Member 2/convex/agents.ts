import { internalQuery } from "./_generated/server";
export const listActive = internalQuery({ args: {}, handler: async (ctx) => ctx.db.query("agents").collect() });
