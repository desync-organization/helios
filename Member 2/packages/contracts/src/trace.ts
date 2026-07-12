import { z } from "zod";
import { EpochMs, ErrorRecord, Sha256, ShortText, externalObject } from "./common";
import { AdapterId, ArtifactId, EventId, RunId, SpanId, TaskId } from "./ids";

export const ExecutionLocation = z.enum(["local_cpu", "local_gpu", "workers_ai", "remote_provider", "tool_sandbox"]);
export const SpanStatus = z.enum(["queued", "running", "succeeded", "failed", "blocked", "cancelled"]);
export const ModelIdentity = z.object({
  baseModel: ShortText,
  baseRevision: ShortText,
  baseSha256: Sha256,
  quantization: ShortText,
  adapterId: AdapterId.optional(),
  adapterVersion: ShortText.optional(),
  adapterSha256: Sha256.optional(),
  adapterScale: z.number().positive().max(100).optional(),
  trainingRunId: z.string().max(128).optional(),
  datasetManifestSha256: Sha256.optional(),
  promptVersion: ShortText,
  agentVersion: ShortText,
}).strict();

export const ToolCall = z.object({
  tool: ShortText,
  purpose: z.string().min(1).max(1_024),
  status: z.enum(["allowed", "denied", "succeeded", "failed"]),
  latencyMs: z.number().int().nonnegative().max(86_400_000),
}).strict();

export const TraceEvent = externalObject({
  eventId: EventId,
  sequence: z.number().int().positive(),
  taskId: TaskId,
  runId: RunId,
  spanId: SpanId,
  parentSpanId: SpanId.optional(),
  nodeId: z.string().regex(/^node_[A-Za-z0-9_-]{1,80}$/),
  agent: ShortText,
  model: ModelIdentity,
  promptHash: Sha256,
  inputArtifactRefs: z.array(ArtifactId).max(200),
  outputArtifactRef: ArtifactId.optional(),
  tokensIn: z.number().int().nonnegative(),
  tokensOut: z.number().int().nonnegative(),
  costUsd: z.number().nonnegative(),
  costCloudEquivalentUsd: z.number().nonnegative(),
  latencyMs: z.number().int().nonnegative(),
  executionLocation: ExecutionLocation,
  toolCalls: z.array(ToolCall).max(100),
  status: SpanStatus,
  verdict: z.enum(["pass", "revise", "blocked"]).optional(),
  error: ErrorRecord.optional(),
  startedAt: EpochMs,
  finishedAt: EpochMs.optional(),
});

export type TraceEvent = z.infer<typeof TraceEvent>;
export type ModelIdentity = z.infer<typeof ModelIdentity>;
