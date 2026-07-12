import { z } from "zod";
import { BodyText, EpochMs, GitSha, HttpsUrl, Sha256, ShortText, externalObject } from "./common";
import { ArtifactId, RunId, TaskId, WritebackId } from "./ids";
import { RepoSlug, RepositoryAction } from "./repository";

export const WritebackMode = z.enum(["dry-run", "pr-only", "live"]);
export const PatchFile = z.object({
  path: z.string().min(1).max(512).refine((path) => !path.startsWith("/") && !path.includes(".."), "unsafe repository path"),
  content: z.string().max(2_000_000),
  encoding: z.literal("utf-8"),
}).strict();

const BaseIntent = {
  writebackId: WritebackId,
  taskId: TaskId,
  runId: RunId,
  repo: RepoSlug,
  action: RepositoryAction,
  idempotencyKey: z.string().min(16).max(256),
  leaseToken: z.string().min(32).max(256),
  artifactId: ArtifactId,
  artifactHash: Sha256,
  criticArtifactId: ArtifactId,
  baseSha: GitSha.optional(),
  policyRuleIds: z.array(z.string().min(1).max(128)).min(1).max(100),
  requiredChecksPassed: z.boolean(),
  securityChecksPassed: z.boolean(),
  testsPassed: z.boolean(),
  breakingChange: z.boolean(),
  requestedAt: EpochMs,
} as const;

export const CommentPayload = z.object({ issueNumber: z.number().int().positive(), body: BodyText }).strict();
export const LabelsPayload = z.object({ issueNumber: z.number().int().positive(), labels: z.array(ShortText).min(1).max(20) }).strict();
export const MilestonePayload = z.object({ issueNumber: z.number().int().positive(), milestoneNumber: z.number().int().positive() }).strict();
export const DuplicatePayload = z.object({ issueNumber: z.number().int().positive(), duplicateOf: z.number().int().positive(), comment: BodyText, confidence: z.number().min(0).max(1) }).strict();
export const BranchPrPayload = z.object({
  branch: z.string().regex(/^hermes\/[a-z0-9][a-z0-9/_-]{0,100}$/),
  title: z.string().min(1).max(256),
  body: BodyText,
  files: z.array(PatchFile).min(1).max(1_000),
  draft: z.boolean().default(false),
}).strict();
export const ReviewPayload = z.object({ pullNumber: z.number().int().positive(), body: BodyText, commitId: GitSha, path: z.string().min(1).max(512), line: z.number().int().positive() }).strict();
export const MergePayload = z.object({ pullNumber: z.number().int().positive(), expectedHeadSha: GitSha, method: z.enum(["merge", "squash", "rebase"]) }).strict();
export const ReleasePayload = z.object({ tagName: ShortText, name: ShortText, body: BodyText, targetCommitish: ShortText, draft: z.literal(true) }).strict();
export const SarifPayload = z.object({ commitSha: GitSha, ref: z.string().min(1).max(512), sarifGzipBase64: z.string().min(1).max(10_000_000) }).strict();
export const StatusCommentPayload = z.object({ issueNumber: z.number().int().positive(), body: BodyText }).strict();

export const WritebackPayload = z.discriminatedUnion("action", [
  z.object({ action: z.literal("comment"), data: CommentPayload }).strict(),
  z.object({ action: z.literal("labels_set"), data: LabelsPayload }).strict(),
  z.object({ action: z.literal("milestone_set"), data: MilestonePayload }).strict(),
  z.object({ action: z.literal("duplicate_close"), data: DuplicatePayload }).strict(),
  z.object({ action: z.literal("branch_and_pr"), data: BranchPrPayload }).strict(),
  z.object({ action: z.literal("build_branch_and_pr"), data: BranchPrPayload }).strict(),
  z.object({ action: z.literal("security_pr"), data: BranchPrPayload }).strict(),
  z.object({ action: z.literal("policy_commit"), data: BranchPrPayload }).strict(),
  z.object({ action: z.literal("eval_case_commit"), data: BranchPrPayload }).strict(),
  z.object({ action: z.literal("pr_review_comment"), data: ReviewPayload }).strict(),
  z.object({ action: z.literal("pr_merge"), data: MergePayload }).strict(),
  z.object({ action: z.literal("release_draft"), data: ReleasePayload }).strict(),
  z.object({ action: z.literal("sarif_upload"), data: SarifPayload }).strict(),
  z.object({ action: z.literal("build_status_comment"), data: StatusCommentPayload }).strict(),
  z.object({ action: z.literal("security_issue_draft"), data: z.object({ title: ShortText, body: BodyText, private: z.literal(true) }).strict() }).strict(),
]);

export const WritebackIntent = externalObject({ ...BaseIntent, payload: WritebackPayload }).refine((intent) => intent.action === intent.payload.action, { message: "action and payload mismatch", path: ["payload", "action"] });
export const WritebackResult = externalObject({
  writebackId: WritebackId,
  status: z.enum(["denied", "dry_run", "pending", "completed", "failed"]),
  policyDecision: z.object({ allowed: z.boolean(), ruleIds: z.array(z.string()), reasonCode: z.string(), message: z.string() }).strict(),
  resultUrl: HttpsUrl.optional(),
  externalId: z.string().max(256).optional(),
  completedAt: EpochMs.optional(),
  error: z.string().max(2_048).optional(),
});

export type WritebackMode = z.infer<typeof WritebackMode>;
export type WritebackIntent = z.infer<typeof WritebackIntent>;
export type WritebackResult = z.infer<typeof WritebackResult>;
export type BranchPrPayload = z.infer<typeof BranchPrPayload>;
