import { z } from "zod";
import { EpochMs, HttpsUrl, Sha256, ShortText, externalObject } from "./common";
import { EvalCaseId, EvalRunId } from "./ids";
import { HermesMode } from "./task";

export const EvalCandidate = externalObject({
  evalCaseId: EvalCaseId,
  mode: HermesMode,
  status: z.enum(["pending-review", "approved", "rejected"]),
  trigger: z.enum(["critic_blocked", "run_failed", "run_escalated", "human_edit", "human_reject", "maintainer_correction", "false_positive", "build_ci_failed", "pr_reverted"]),
  inputRedacted: z.string().max(32_000),
  wrongOutputRedacted: z.string().max(32_000),
  correctionRedacted: z.string().max(32_000).optional(),
  sourceUrl: HttpsUrl.optional(),
  versionFingerprint: Sha256,
  createdAt: EpochMs,
});

export const EvalRun = externalObject({
  evalRunId: EvalRunId,
  mode: HermesMode,
  configurationVersion: ShortText,
  reportSha256: Sha256,
  score: z.number().min(0).max(1),
  thresholds: z.record(z.string(), z.number().min(0).max(1)),
  passed: z.boolean(),
  secretLeakCount: z.number().int().nonnegative(),
  unauthorizedActionCount: z.number().int().nonnegative(),
  createdAt: EpochMs,
});

export type EvalCandidate = z.infer<typeof EvalCandidate>;
export type EvalRun = z.infer<typeof EvalRun>;
