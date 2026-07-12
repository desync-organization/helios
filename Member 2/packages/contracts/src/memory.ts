import { z } from "zod";
import { EpochMs, RetentionClass, ShortText, externalObject } from "./common";
import { EntityId, TaskId } from "./ids";
import { RepoSlug } from "./repository";

export const MemoryLayer = z.enum(["now", "entity_history", "business_policy"]);
export const EntityKind = z.enum(["user", "issue", "repository", "project", "security_finding"]);
export const MemoryRecord = externalObject({
  entityId: EntityId,
  repo: RepoSlug,
  layer: MemoryLayer,
  kind: EntityKind,
  externalKey: z.string().min(1).max(512),
  summaryRedacted: z.string().max(8_192),
  sourceTaskIds: z.array(TaskId).max(100),
  retentionClass: RetentionClass,
  expiresAt: EpochMs,
  createdAt: EpochMs,
  updatedAt: EpochMs,
});

export type MemoryRecord = z.infer<typeof MemoryRecord>;
