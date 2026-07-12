import type { HermesMode, TaskType } from "../../../packages/contracts/src/task";
import { redactSensitive } from "../../../src/security/redaction";

const SUPPORTED_EVENTS = new Set([
  "issues", "issue_comment", "pull_request", "pull_request_review", "workflow_run", "release",
  "security_advisory", "repository_vulnerability_alert", "dependabot_alert", "secret_scanning_alert", "code_scanning_alert",
]);

interface Actor { login?: string; type?: string }
interface Repository { full_name?: string; private?: boolean; html_url?: string; id?: number }

export interface NormalizedWebhook {
  schemaVersion: 1;
  deliveryId: string;
  event: string;
  action: string;
  repo: string;
  repositoryId?: number;
  mode: HermesMode;
  type: TaskType;
  dedupeKey: string;
  requestedBy: string;
  dataClassification: "public" | "private";
  payloadRedacted: string;
  sourceUrl?: string;
}

function object(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
function text(value: unknown): string | undefined { return typeof value === "string" ? value : undefined; }
function number(value: unknown): number | undefined { return typeof value === "number" ? value : undefined; }

export function isHermesAuthored(payload: Record<string, unknown>, botLogin: string): boolean {
  const sender = object(payload.sender) as Actor;
  const comment = object(payload.comment);
  const issue = object(payload.issue);
  const pull = object(payload.pull_request);
  const body = [text(comment.body), text(issue.body), text(pull.body)].filter(Boolean).join("\n");
  return sender.login?.toLowerCase() === botLogin.toLowerCase() || sender.type === "Bot" && body.includes("<!-- hermes:writeback -->") || body.includes("<!-- hermes:writeback -->");
}

function mapTask(event: string, action: string): { mode: HermesMode; type: TaskType } {
  if (["security_advisory", "repository_vulnerability_alert", "dependabot_alert", "secret_scanning_alert", "code_scanning_alert"].includes(event)) {
    return { mode: "security_audit", type: event === "secret_scanning_alert" ? "secret_scan" : event === "code_scanning_alert" ? "sast" : "vulnerability_triage" };
  }
  if (event === "pull_request" || event === "pull_request_review") return { mode: "maintain", type: "review" };
  if (event === "workflow_run") return { mode: "maintain", type: action === "completed" ? "fix" : "intake" };
  if (event === "release") return { mode: "maintain", type: "release" };
  if (event === "issue_comment") return { mode: "maintain", type: "respond" };
  return { mode: "maintain", type: "intake" };
}

export async function normalizeGitHubWebhook(event: string, deliveryId: string, payload: Record<string, unknown>): Promise<NormalizedWebhook | null> {
  if (!SUPPORTED_EVENTS.has(event)) return null;
  const repository = object(payload.repository) as Repository;
  const repo = repository.full_name;
  if (!repo || !/^[A-Za-z0-9_.-]{1,100}\/[A-Za-z0-9_.-]{1,100}$/.test(repo)) return null;
  const action = text(payload.action) ?? "unknown";
  const sender = object(payload.sender) as Actor;
  const issue = object(payload.issue);
  const pull = object(payload.pull_request);
  const alert = object(payload.alert);
  const sourceUrl = text(issue.html_url) ?? text(pull.html_url) ?? text(alert.html_url) ?? repository.html_url;
  const sourceNumber = number(issue.number) ?? number(pull.number) ?? number(alert.number) ?? "repository";
  const fields = {
    action,
    issue: issue.number ? { number: issue.number, title: issue.title, body: issue.body, labels: issue.labels, html_url: issue.html_url } : undefined,
    pull_request: pull.number ? { number: pull.number, title: pull.title, body: pull.body, base: pull.base, head: pull.head, html_url: pull.html_url } : undefined,
    comment: payload.comment ? { id: object(payload.comment).id, body: object(payload.comment).body, html_url: object(payload.comment).html_url } : undefined,
    alert: payload.alert ? { number: alert.number, state: alert.state, dependency: alert.dependency, security_advisory: alert.security_advisory, html_url: alert.html_url } : undefined,
  };
  const redacted = await redactSensitive(JSON.stringify(fields), true);
  const mapped = mapTask(event, action);
  return {
    schemaVersion: 1,
    deliveryId,
    event,
    action,
    repo,
    repositoryId: repository.id,
    ...mapped,
    dedupeKey: `${deliveryId}:${event}:${action}:${repo}:${sourceNumber}`,
    requestedBy: sender.login ?? "github",
    dataClassification: repository.private ? "private" : "public",
    payloadRedacted: redacted.value,
    ...(sourceUrl?.startsWith("https://") ? { sourceUrl } : {}),
  };
}
