import { z } from "zod";
import { EpochMs, ShortText, externalObject } from "./common";

export const RepoSlug = z.string().regex(/^[A-Za-z0-9_.-]{1,100}\/[A-Za-z0-9_.-]{1,100}$/);
export const RepositoryVisibility = z.enum(["public", "private", "internal"]);
export const ProviderName = z.enum(["workers_ai", "haiku", "linkup", "osv", "github_advisory", "elevenlabs"]);
export const RepositoryAction = z.enum([
  "comment", "labels_set", "milestone_set", "duplicate_close", "branch_and_pr",
  "pr_review_comment", "pr_merge", "release_draft", "policy_commit", "eval_case_commit",
  "security_issue_draft", "security_pr", "sarif_upload", "build_branch_and_pr", "build_status_comment",
]);

export const RetentionPolicy = z.object({
  artifactDays: z.number().int().min(1).max(3650),
  entityDays: z.number().int().min(1).max(3650),
  providerPayloadHours: z.number().int().min(0).max(168),
  voiceAudioMinutes: z.number().int().min(0).max(60),
  scannerOutputHours: z.number().int().min(1).max(720),
}).strict();

export const RepositoryDescriptor = externalObject({
  repo: RepoSlug,
  defaultBranch: ShortText,
  visibility: RepositoryVisibility,
  writebackOptIn: z.boolean(),
  securityAuditOptIn: z.boolean(),
  allowedActions: z.array(RepositoryAction).max(20),
  allowedCloudProviders: z.array(ProviderName).max(10),
  protectedPaths: z.array(z.string().min(1).max(512)).max(100),
  sizeLimits: z.object({ maxPatchBytes: z.number().int().positive().max(10_000_000), maxFiles: z.number().int().positive().max(1_000) }).strict(),
  requiredChecks: z.array(ShortText).max(100),
  activePolicyVersion: ShortText,
  retentionPolicy: RetentionPolicy,
  health: z.enum(["healthy", "degraded", "disabled"]),
  updatedAt: EpochMs,
});

export type RepoSlug = z.infer<typeof RepoSlug>;
export type ProviderName = z.infer<typeof ProviderName>;
export type RepositoryAction = z.infer<typeof RepositoryAction>;
export type RepositoryDescriptor = z.infer<typeof RepositoryDescriptor>;
