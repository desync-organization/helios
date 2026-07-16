import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";

const DEFAULT_STATE = {
  globalPaused: false,
  emergencyMode: false,
  pausedAgents: [] as string[],
  writebackMode: "dry-run",
  securityScanMode: "read-only",
  currentAgentTag: "agents-v1",
  currentAdapterPointers: {} as Record<string, string>,
  updatedAt: 0,
};

function validatedPatch(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("INVALID_CONTROL_PATCH");
  const patch = value as Record<string, unknown>;
  const allowedKeys = new Set([
    "globalPaused", "emergencyMode", "pausedAgents", "writebackMode",
    "securityScanMode", "currentAgentTag", "currentAdapterPointers",
  ]);
  if (Object.keys(patch).some((key) => !allowedKeys.has(key))) throw new Error("INVALID_CONTROL_PATCH");
  if (patch.globalPaused !== undefined && typeof patch.globalPaused !== "boolean") throw new Error("INVALID_CONTROL_PATCH");
  if (patch.emergencyMode !== undefined && typeof patch.emergencyMode !== "boolean") throw new Error("INVALID_CONTROL_PATCH");
  if (patch.writebackMode !== undefined && !["dry-run", "pr-only", "live"].includes(String(patch.writebackMode))) throw new Error("INVALID_CONTROL_PATCH");
  if (patch.securityScanMode !== undefined && !["read-only", "remediation-approved"].includes(String(patch.securityScanMode))) throw new Error("INVALID_CONTROL_PATCH");
  if (patch.currentAgentTag !== undefined && (typeof patch.currentAgentTag !== "string" || patch.currentAgentTag.length < 1 || patch.currentAgentTag.length > 256)) throw new Error("INVALID_CONTROL_PATCH");
  if (patch.pausedAgents !== undefined) {
    if (!Array.isArray(patch.pausedAgents) || patch.pausedAgents.length > 200 || patch.pausedAgents.some((agent) => typeof agent !== "string" || agent.length < 1 || agent.length > 256)) throw new Error("INVALID_CONTROL_PATCH");
    patch.pausedAgents = [...new Set(patch.pausedAgents)];
  }
  if (patch.currentAdapterPointers !== undefined) {
    if (!patch.currentAdapterPointers || typeof patch.currentAdapterPointers !== "object" || Array.isArray(patch.currentAdapterPointers)) throw new Error("INVALID_CONTROL_PATCH");
    const entries = Object.entries(patch.currentAdapterPointers as Record<string, unknown>);
    if (entries.length > 200 || entries.some(([role, adapter]) => !/^[A-Za-z0-9._-]{1,128}$/.test(role) || typeof adapter !== "string" || adapter.length < 1 || adapter.length > 256)) throw new Error("INVALID_CONTROL_PATCH");
  }
  return patch;
}

export const get = internalQuery({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    if (!state) return DEFAULT_STATE;
    return {
      globalPaused: state.globalPaused,
      emergencyMode: state.emergencyMode,
      pausedAgents: state.pausedAgents,
      writebackMode: state.writebackMode,
      securityScanMode: state.securityScanMode,
      currentAgentTag: state.currentAgentTag,
      currentAdapterPointers: state.currentAdapterPointers,
      updatedAt: state.updatedAt,
    };
  },
});
export const update = internalMutation({
  args: { patch: v.any(), now: v.number() },
  handler: async (ctx, { patch, now }) => {
    const existing = await ctx.db.query("systemState").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    const current = existing ? { globalPaused: existing.globalPaused, emergencyMode: existing.emergencyMode, pausedAgents: existing.pausedAgents, writebackMode: existing.writebackMode, securityScanMode: existing.securityScanMode, currentAgentTag: existing.currentAgentTag, currentAdapterPointers: existing.currentAdapterPointers } : {};
    const next = { ...DEFAULT_STATE, ...current, ...validatedPatch(patch), key: "global", updatedAt: now };
    if (existing) { await ctx.db.patch(existing._id, next); return existing._id; }
    return ctx.db.insert("systemState", next);
  },
});
