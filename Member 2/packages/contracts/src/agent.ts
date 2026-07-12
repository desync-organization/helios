import { z } from "zod";
import { EpochMs, Sha256, ShortText, externalObject } from "./common";
import { AdapterId, AgentId } from "./ids";
import { ModelIdentity } from "./trace";

export const AgentOrigin = z.enum(["kickoff", "spawned", "operator_created"]);
export const Agent = externalObject({
  agentId: AgentId,
  name: ShortText,
  version: ShortText,
  origin: AgentOrigin,
  role: ShortText,
  personaHash: Sha256,
  toolGrants: z.array(ShortText).max(50),
  model: ModelIdentity,
  activeAdapterId: AdapterId.optional(),
  immutable: z.literal(true),
  createdAt: EpochMs,
});

export type Agent = z.infer<typeof Agent>;
