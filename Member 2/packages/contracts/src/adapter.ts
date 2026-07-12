import { z } from "zod";
import { EpochMs, Sha256, ShortText, externalObject } from "./common";
import { AdapterId, EvalRunId } from "./ids";

export const AdapterPromotionStatus = z.enum(["candidate", "approved", "active", "rolled_back", "rejected"]);
export const Adapter = externalObject({
  adapterId: AdapterId,
  version: ShortText,
  baseModel: ShortText,
  baseRevision: ShortText,
  baseSha256: Sha256,
  tokenizerSha256: Sha256,
  adapterSha256: Sha256,
  trainingRunId: ShortText,
  datasetManifestSha256: Sha256,
  evalReportSha256: Sha256,
  heldOutEvalRunId: EvalRunId,
  tenRunBenchmarkPassed: z.boolean(),
  stableGauntletRuns: z.array(EvalRunId).length(3),
  safetySubgroupsPassed: z.boolean(),
  qualityApprovedBy: ShortText,
  compatibilityApprovedBy: ShortText,
  activeRoles: z.array(ShortText).min(1).max(50),
  rollbackPredecessorId: AdapterId.optional(),
  status: AdapterPromotionStatus,
  createdAt: EpochMs,
});

export type Adapter = z.infer<typeof Adapter>;
