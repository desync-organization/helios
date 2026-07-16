import { z } from "zod";
import { BodyText, DataClassification, EpochMs, HttpsUrl, ShortText, externalObject } from "./common";
import { BacklogBatchId, TaskId } from "./ids";
import { ProviderName, RepoSlug, RepositoryAction, ScannerName } from "./repository";

export const HermesMode = z.enum(["maintain", "build", "security_audit"]);
export const TaskType = z.enum([
  "intake", "classify", "label", "dedupe", "clarify", "respond", "repro", "fix", "review", "docs", "release", "escalate",
  "requirements", "architecture", "implement", "integrate", "package", "dependency_audit", "secret_scan", "sast", "config_audit",
  "threat_model", "vulnerability_triage", "security_remediate", "role_test", "eval",
]);
export const TaskStatus = z.enum(["pending", "claimed", "running", "done", "failed", "escalated"]);
export const TaskSource = z.discriminatedUnion("kind", [
  z.object({ kind: z.literal("github"), event: ShortText, deliveryId: ShortText, sourceUrl: HttpsUrl.optional() }).strict(),
  z.object({ kind: z.literal("operator"), promptId: ShortText.optional() }).strict(),
  z.object({ kind: z.literal("backlog"), batchId: BacklogBatchId }).strict(),
  z.object({ kind: z.literal("system"), reason: ShortText }).strict(),
]);

export const ConsentScope = z.object({
  repo: RepoSlug,
  allowedActions: z.array(RepositoryAction).max(20),
  allowedCloudProviders: z.array(ProviderName).max(10),
  allowedScanners: z.array(ScannerName).max(10).default([]),
  privateCodeMayLeaveDevice: z.boolean(),
  externalSecurityUploadAllowed: z.boolean().default(false),
  expiresAt: EpochMs,
  grantedBy: ShortText,
  consentRef: ShortText,
}).strict();

export const Lease = z.object({
  ownerId: z.string().min(1).max(128),
  token: z.string().min(32).max(256),
  acquiredAt: EpochMs,
  expiresAt: EpochMs,
  heartbeatAt: EpochMs,
}).strict().refine((lease) => lease.expiresAt > lease.acquiredAt, "lease must expire after acquisition");

export const Task = externalObject({
  taskId: TaskId,
  source: TaskSource,
  mode: HermesMode,
  type: TaskType,
  repo: RepoSlug,
  payload: BodyText,
  status: TaskStatus,
  dedupeKey: z.string().min(1).max(512),
  requestedBy: ShortText,
  consentScope: ConsentScope,
  dataClassification: DataClassification,
  policyVersion: ShortText,
  approvedBacklogBatchId: BacklogBatchId.optional(),
  lease: Lease.optional(),
  resultUrls: z.array(HttpsUrl).max(50),
  createdAt: EpochMs,
  updatedAt: EpochMs,
}).refine((task) => task.consentScope.repo === task.repo, { message: "consent repository mismatch", path: ["consentScope", "repo"] });

export type HermesMode = z.infer<typeof HermesMode>;
export type TaskType = z.infer<typeof TaskType>;
export type TaskStatus = z.infer<typeof TaskStatus>;
export type ConsentScope = z.infer<typeof ConsentScope>;
export type Lease = z.infer<typeof Lease>;
export type Task = z.infer<typeof Task>;
