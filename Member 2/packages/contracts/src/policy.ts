import { z } from "zod";
import { EpochMs, ShortText, externalObject } from "./common";
import { PolicyId } from "./ids";
import { RepoSlug, RepositoryAction } from "./repository";

export const PolicySeverity = z.enum(["info", "warning", "blocking", "critical"]);
export const PolicyRule = z.object({
  id: z.string().regex(/^[a-z][a-z0-9_.-]{2,127}$/),
  description: z.string().min(1).max(2_048),
  severity: PolicySeverity,
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  enabled: z.boolean(),
  parameters: z.record(z.string(), z.unknown()),
}).strict();

export const PolicyBundle = externalObject({
  policyId: PolicyId,
  repo: RepoSlug,
  version: ShortText,
  rules: z.array(PolicyRule).min(1).max(500),
  allowedActions: z.array(RepositoryAction).max(20),
  activatedAt: EpochMs,
  gitCommitSha: z.string().regex(/^[a-f0-9]{40}$/i),
});

export const PolicyDecision = externalObject({
  allowed: z.boolean(),
  ruleIds: z.array(z.string().max(128)).max(100),
  reasonCode: z.string().min(1).max(64),
  message: z.string().min(1).max(2_048),
  decidedAt: EpochMs,
});

export type PolicyRule = z.infer<typeof PolicyRule>;
export type PolicyBundle = z.infer<typeof PolicyBundle>;
export type PolicyDecision = z.infer<typeof PolicyDecision>;
