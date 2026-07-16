import type { RepositoryDescriptor } from "../../packages/contracts/src/repository";
import type { Task } from "../../packages/contracts/src/task";
import type { WritebackIntent, WritebackMode } from "../../packages/contracts/src/writeback";
import type { SystemState } from "../control/state";
import { containsSuspectedSecret } from "../security/redaction";

export interface CriticApproval {
  artifactId: string;
  reviewedArtifactId: string;
  reviewedContentHash: string;
  verdict: "pass" | "revise" | "blocked";
  producerAgent: string;
  criticAgent: string;
}

export interface WritebackPolicyContext {
  intent: WritebackIntent;
  task: Task;
  repository: RepositoryDescriptor;
  state: SystemState;
  critic: CriticApproval;
  currentBaseSha?: string;
  changedPaths?: string[];
  patchBytes?: number;
  now: number;
}

export interface Decision { allowed: boolean; reasonCode: string; message: string; ruleIds: string[] }

const PR_ACTIONS = new Set(["branch_and_pr", "build_branch_and_pr", "security_pr", "policy_commit", "eval_case_commit"]);
const HARD_NEVER = new Set(["force_push", "branch_delete", "settings_mutation", "secret_access", "release_publish", "advisory_publish"]);

function deny(reasonCode: string, message: string, ...ruleIds: string[]): Decision { return { allowed: false, reasonCode, message, ruleIds }; }
function allowed(...ruleIds: string[]): Decision { return { allowed: true, reasonCode: "ALLOWED", message: "All write-back gates passed", ruleIds }; }

function matchesProtectedPath(path: string, patterns: string[]): boolean {
  return patterns.some((pattern) => {
    const normalized = pattern.replace(/^\//, "");
    if (normalized.endsWith("/**")) return path === normalized.slice(0, -3) || path.startsWith(normalized.slice(0, -2));
    if (normalized.endsWith("*")) return path.startsWith(normalized.slice(0, -1));
    return path === normalized || path.startsWith(`${normalized}/`);
  });
}

export function evaluateWriteback(context: WritebackPolicyContext): Decision {
  const { intent, task, repository, state, critic, now } = context;
  if (HARD_NEVER.has(intent.action)) return deny("HARD_NEVER", "This action is prohibited by invariant", "autonomy.hard-never");
  if (state.emergencyMode || state.globalPaused) return deny("SYSTEM_PAUSED", "Write-back is disabled by current system state", "autonomy.pause");
  if (state.pausedAgents.includes(critic.producerAgent)) return deny("AGENT_PAUSED", "The producing agent is paused", "autonomy.pause");
  if (repository.repo !== intent.repo || task.repo !== intent.repo || task.consentScope.repo !== intent.repo) return deny("REPOSITORY_MISMATCH", "Repository identity does not match the task, consent, and onboarding record", "repository.isolation");
  if (repository.health !== "healthy" || !repository.writebackOptIn) return deny("REPOSITORY_DISABLED", "Repository is not healthy and opted in for write-back", "repository.allowlisted");
  if (!repository.allowedActions.includes(intent.action) || !task.consentScope.allowedActions.includes(intent.action)) return deny("ACTION_NOT_ALLOWED", "Action is not allowed by repository policy and task consent", "consent.action");
  if (task.consentScope.expiresAt <= now) return deny("CONSENT_EXPIRED", "Task consent has expired", "consent.expiry");
  if (!task.lease || task.lease.token !== intent.leaseToken || task.lease.expiresAt <= now) return deny("LOST_LEASE", "A current task lease is required immediately before mutation", "lease.current");
  if (critic.verdict !== "pass" || critic.artifactId !== intent.criticArtifactId || critic.reviewedArtifactId !== intent.artifactId || critic.reviewedContentHash !== intent.artifactHash) return deny("CRITIC_MISMATCH", "Independent critic did not pass the exact artifact hash", "autonomy.critic.exact-hash");
  if (critic.producerAgent === critic.criticAgent) return deny("CRITIC_NOT_INDEPENDENT", "Producer and critic identities must differ", "autonomy.critic.exact-hash");
  if (!intent.testsPassed || !intent.securityChecksPassed || !intent.requiredChecksPassed) return deny("QUALITY_GATES_FAILED", "Tests, security, and required checks must all pass", "build.quality.gates");
  if (intent.breakingChange) return deny("BREAKING_CHANGE", "Breaking changes require human escalation", "escalation.material-decision");
  if (state.writebackMode === "dry-run") return deny("DRY_RUN", "Dry-run mode records the decision but performs no external mutation", "autonomy.dry-run");
  if (state.writebackMode === "pr-only" && !PR_ACTIONS.has(intent.action)) return deny("PR_ONLY", "Current mode permits pull-request delivery only", "autonomy.pr-only");
  if (task.mode === "security_audit" && state.securityScanMode === "read-only") return deny("SECURITY_READ_ONLY", "Read-only security audit cannot mutate GitHub", "security.audit.read-only");
  if (intent.action === "security_issue_draft") return deny("PUBLIC_SECURITY_DISCLOSURE_DISABLED", "Security findings remain in restricted private review", "security.disclosure.private");
  if (intent.action === "pr_merge" && !repository.requiredChecks.length) return deny("MERGE_POLICY_INCOMPLETE", "Autonomous merge requires configured required checks", "autonomy.merge.bounded");
  if (intent.action === "release_draft" && intent.payload.action === "release_draft" && !intent.payload.data.draft) return deny("RELEASE_PUBLISH_DENIED", "Only draft releases are permitted", "autonomy.hard-never");
  if (intent.baseSha && context.currentBaseSha && intent.baseSha !== context.currentBaseSha) return deny("BASE_SHA_CONFLICT", "Repository base SHA changed after artifact production", "writeback.base-sha");
  if ((context.patchBytes ?? 0) > repository.sizeLimits.maxPatchBytes) return deny("PATCH_TOO_LARGE", "Patch exceeds repository size policy", "writeback.size-limit");
  const paths = context.changedPaths ?? [];
  if (paths.length > repository.sizeLimits.maxFiles) return deny("TOO_MANY_FILES", "Patch exceeds repository file-count policy", "writeback.size-limit");
  if (paths.some((path) => matchesProtectedPath(path, repository.protectedPaths))) return deny("PROTECTED_PATH", "A protected path requires human escalation", "escalation.protected-path");
  if (intent.payload.action === "branch_and_pr" || intent.payload.action === "build_branch_and_pr" || intent.payload.action === "security_pr" || intent.payload.action === "policy_commit" || intent.payload.action === "eval_case_commit") {
    if (intent.payload.data.files.some((file) => containsSuspectedSecret(file.content))) return deny("SECRET_IN_PATCH", "Patch contains suspected secret material", "security.secret.never-persist");
  }
  return allowed("autonomy.critic.exact-hash", "consent.action", "lease.current", "writeback.idempotent");
}

export function modeAllowsExternalMutation(mode: WritebackMode): boolean { return mode !== "dry-run"; }
