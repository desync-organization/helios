import { z } from "zod";
import { EpochMs, ShortText, externalObject } from "./common";
import { AlertId, RunId, TaskId } from "./ids";
import { RepoSlug } from "./repository";

export const AlertKind = z.enum(["task_failure", "run_failure", "lease_expiry", "cost_spike", "latency_spike", "escalation", "eval_regression", "adapter_mismatch", "scanner_failure", "secret_finding", "provider_outage", "writeback_denial"]);
export const AlertEvent = externalObject({
  alertId: AlertId,
  kind: AlertKind,
  severity: z.enum(["info", "warning", "critical"]),
  repo: RepoSlug.optional(),
  taskId: TaskId.optional(),
  runId: RunId.optional(),
  messageRedacted: z.string().min(1).max(4_096),
  ruleId: ShortText,
  acknowledgedAt: EpochMs.optional(),
  createdAt: EpochMs,
});

export type AlertEvent = z.infer<typeof AlertEvent>;
export type AlertKind = z.infer<typeof AlertKind>;
