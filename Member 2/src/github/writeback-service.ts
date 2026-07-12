import { SCHEMA_VERSION } from "../../packages/contracts/src/common";
import type { RepositoryDescriptor } from "../../packages/contracts/src/repository";
import type { Task } from "../../packages/contracts/src/task";
import { WritebackResult, type WritebackIntent, type WritebackResult as WritebackResultValue } from "../../packages/contracts/src/writeback";
import type { SystemState } from "../control/state";
import { ControlPlaneError } from "../errors";
import { evaluateWriteback, type CriticApproval } from "../policy/writeback-policy";

export interface GitHubExecutionContext {
  installationId: number;
  defaultBranch: string;
  currentBaseSha?: string;
}

export interface GitHubExecutor {
  execute(intent: WritebackIntent, context: GitHubExecutionContext): Promise<{ resultUrl: string; externalId: string }>;
}

export interface WritebackContext {
  task: Task;
  repository: RepositoryDescriptor;
  installationId: number;
  state: SystemState;
  critic: CriticApproval;
  currentBaseSha?: string;
  now?: number;
}

export class WritebackService {
  private readonly completed = new Map<string, WritebackResultValue>();
  private readonly inFlight = new Set<string>();
  constructor(private readonly executor: GitHubExecutor) {}

  async perform(intent: WritebackIntent, context: WritebackContext): Promise<WritebackResultValue> {
    const replay = this.completed.get(`${intent.repo}:${intent.idempotencyKey}`);
    if (replay) return structuredClone(replay);
    const key = `${intent.repo}:${intent.idempotencyKey}`;
    if (this.inFlight.has(key)) throw new ControlPlaneError("CONFLICT", "An identical write-back is already in progress", 409, true);
    const paths = intent.payload.action === "branch_and_pr" || intent.payload.action === "build_branch_and_pr" || intent.payload.action === "security_pr" || intent.payload.action === "policy_commit" || intent.payload.action === "eval_case_commit"
      ? intent.payload.data.files.map((file) => file.path) : [];
    const patchBytes = intent.payload.action === "branch_and_pr" || intent.payload.action === "build_branch_and_pr" || intent.payload.action === "security_pr" || intent.payload.action === "policy_commit" || intent.payload.action === "eval_case_commit"
      ? intent.payload.data.files.reduce((sum, file) => sum + new TextEncoder().encode(file.content).byteLength, 0) : 0;
    const decision = evaluateWriteback({ intent, ...context, changedPaths: paths, patchBytes, now: context.now ?? Date.now() });
    if (!decision.allowed) {
      const denied = WritebackResult.parse({ schemaVersion: SCHEMA_VERSION, writebackId: intent.writebackId, status: decision.reasonCode === "DRY_RUN" ? "dry_run" : "denied", policyDecision: decision });
      if (decision.reasonCode === "DRY_RUN") this.completed.set(key, denied);
      return denied;
    }
    this.inFlight.add(key);
    try {
      const external = await this.executor.execute(intent, { installationId: context.installationId, defaultBranch: context.repository.defaultBranch, currentBaseSha: context.currentBaseSha });
      if (!external.resultUrl.startsWith("https://")) throw new ControlPlaneError("UPSTREAM_FAILED", "GitHub did not return a valid HTTPS result URL", 502, true);
      const result = WritebackResult.parse({
        schemaVersion: SCHEMA_VERSION,
        writebackId: intent.writebackId,
        status: "completed",
        policyDecision: decision,
        resultUrl: external.resultUrl,
        externalId: external.externalId,
        completedAt: context.now ?? Date.now(),
      });
      this.completed.set(key, result);
      return structuredClone(result);
    } finally {
      this.inFlight.delete(key);
    }
  }
}
