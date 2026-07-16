import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { internal } from "./_generated/api";

const http = httpRouter();

function json(value: unknown, status = 200, headers?: HeadersInit): Response { return Response.json(value, { status, headers }); }
function error(status: number, code: string, message: string, retryable = false, headers?: HeadersInit): Response { return json({ error: { code, message, retryable } }, status, headers); }
function constantTimeEqual(left: string, right: string): boolean { const length = Math.max(left.length, right.length, 1); let difference = left.length ^ right.length; for (let i = 0; i < length; i += 1) difference |= (left.charCodeAt(i) || 0) ^ (right.charCodeAt(i) || 0); return difference === 0; }
function authorized(request: Request, name: "CONTROL_PLANE_INGEST_TOKEN" | "RUNTIME_BEARER_TOKEN" | "GATEWAY_BEARER_TOKEN"): boolean {
    const expected = name === "CONTROL_PLANE_INGEST_TOKEN"
        ? process.env.CONTROL_PLANE_INGEST_TOKEN ?? ""
        : name === "RUNTIME_BEARER_TOKEN"
            ? process.env.RUNTIME_BEARER_TOKEN ?? ""
            : process.env.GATEWAY_BEARER_TOKEN ?? "";
    const header = request.headers.get("Authorization") ?? "";
    return expected.length >= 32 && header.startsWith("Bearer ") && constantTimeEqual(header.slice(7), expected);
}
async function body(request: Request, maximumBytes = 512_000): Promise<any> { const declared = Number(request.headers.get("Content-Length") ?? "0"); if (declared > maximumBytes) throw new RangeError("TOO_LARGE"); const raw = await request.arrayBuffer(); if (raw.byteLength > maximumBytes) throw new RangeError("TOO_LARGE"); return JSON.parse(new TextDecoder().decode(raw)); }
async function sha256(value: string): Promise<string> { const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)); return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join(""); }
function canonicalJson(value: any): string { if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`; if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`; return JSON.stringify(value); }
function newDomainId(prefix: string): string { return `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 26).toUpperCase()}`; }
function domainProjection<T>(value: T): T { return JSON.parse(JSON.stringify(value, (key, item) => ["_id", "_creationTime", "leaseTokenHash", "installationId", "githubRepositoryId"].includes(key) ? undefined : item)) as T; }
function route(path: string, method: "GET" | "POST", handler: Parameters<typeof http.route>[0]["handler"]): void { http.route({ path, method, handler }); }
function parsedPayload(value: unknown): Record<string, any> { try { const parsed = JSON.parse(String(value ?? "{}")); return parsed && typeof parsed === "object" ? parsed : {}; } catch { return {}; } }
function containsSecretLikeMaterial(value: string): boolean { return /gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|BEGIN .*PRIVATE KEY|(?:AKIA|ASIA)[A-Z0-9]{16}/i.test(value); }
function isSafeHttpsUrl(value: unknown): value is string { try { const parsed = new URL(String(value)); return typeof value === "string" && value.length <= 2_048 && parsed.protocol === "https:" && !parsed.username && !parsed.password; } catch { return false; } }
function runtimeTask(claimed: any, repository: any, memoryPack: any): Record<string, unknown> {
  const payload = parsedPayload(claimed.payloadRedacted);
  const issue = payload.issue ?? {};
  const pull = payload.pull_request ?? {};
  const typeMap: Record<string, string> = { requirements: "feature", architecture: "feature", implement: "feature", integrate: "feature", package: "feature", dependency_audit: "audit", secret_scan: "audit", sast: "audit", config_audit: "audit", threat_model: "audit", vulnerability_triage: "audit", security_remediate: "remediate", role_test: "intake", eval: "intake" };
  const headSha = pull?.head?.sha;
  const issueNumber = Number(issue.number || 0) || undefined;
  const pullNumber = Number(pull.number || 0) || undefined;
  const supportedScanners = new Set(["bandit", "gitleaks", "semgrep", "trivy", "npm", "pip-audit"]);
  const configuredScanners = Array.isArray(claimed.consentScope?.allowedScanners)
    ? claimed.consentScope.allowedScanners.filter((item: unknown) => typeof item === "string" && supportedScanners.has(item))
    : [];
  return {
    schemaVersion: "1.0",
    taskId: claimed.taskId,
    mode: claimed.mode,
    taskType: typeMap[claimed.type] ?? claimed.type,
    repository: claimed.repo,
    baseSha: typeof headSha === "string" && /^[a-f0-9]{40}$/i.test(headSha) ? headSha : "0".repeat(40),
    policyVersion: claimed.policyVersion,
    title: String(issue.title ?? pull.title ?? payload.prompt ?? `${claimed.type} ${claimed.repo}`).slice(0, 1_024),
    body: String(issue.body ?? pull.body ?? payload.prompt ?? "").slice(0, 128_000),
    source: "github",
    visibility: repository?.visibility ?? claimed.dataClassification,
    consent: {
      repositoryAllowlisted: true,
      securityAuditOptIn: Boolean(repository?.securityAuditOptIn),
      remediationPermitted: claimed.consentScope?.allowedActions?.includes("security_pr") ?? false,
      networkPermitted: (claimed.consentScope?.allowedCloudProviders?.length ?? 0) > 0,
      deploymentPermitted: false,
      allowedScanners: configuredScanners,
      allowedPaths: ["."],
      excludedPaths: [".git", "node_modules"],
      maxRuntimeS: 600,
    },
    memoryPack: Array.isArray(memoryPack) ? { items: memoryPack } : memoryPack ?? {},
    policyPack: { version: claimed.policyVersion, allowedActions: claimed.consentScope?.allowedActions ?? [], trustedLocalExecution: repository?.trustedLocalExecution === true, dependenciesPrepared: false },
    metadata: { issueNumber, pullNumber, sourceUrl: claimed.source?.sourceUrl ?? payload.sourceUrl, dataClassification: claimed.dataClassification, proposedFiles: payload.proposedFiles ?? [], testCommands: payload.testCommands ?? [], ...(claimed.activeRunId ? { resumeRunId: claimed.activeRunId } : {}) },
    createdAt: new Date(claimed.createdAt).toISOString(),
  };
}
function gatewayEvent(event: any): Record<string, unknown> {
  const projection = event.projectionRedacted ?? {};
  const originalType = String(projection.type ?? event.kind ?? "progress");
  const type = originalType === "writeback_completed" ? "complete" : originalType.includes("failed") ? "error" : originalType.includes("artifact") || originalType.includes("node") || originalType.includes("run") || originalType.includes("planner") ? "progress" : "terminal";
  const payload = projection.payload ?? projection;
  const text = type === "complete" ? "GitHub write-back completed" : originalType.replaceAll("_", " ");
  return { schemaVersion: "1.0", eventId: event.eventId, type, src: projection.source ?? "control-plane", dst: "ui", ts: event.createdAt, sequence: event.sequence, taskId: event.taskId, runId: event.runId, spanId: projection.spanId, payload: typeof payload === "object" && payload ? { ...payload, text: payload.text ?? text } : { text }, redactionLevel: "redacted", dataClass: ["fixture", "dry-run", "degraded", "replayed", "live"].includes(event.label) ? event.label : "live", ...(type === "complete" ? { persistedResultUrl: projection.resultUrl } : {}) };
}

route("/ingest/github", "POST", httpAction(async (ctx, request) => {
  if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token");
  try { const webhook = await body(request, 2_000_000); if (webhook.schemaVersion !== 1) return error(422, "SCHEMA_VERSION", "Unsupported schema version"); return json(await ctx.runMutation(internal.ingest.github, { webhook, taskId: newDomainId("tsk"), now: Date.now() }), 202); } catch (cause) { return cause instanceof RangeError ? error(413, "TOO_LARGE", "Payload exceeds limit") : error(422, "VALIDATION_FAILED", "Invalid webhook payload"); }
}));
route("/ingest/dead-letter", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { return json(await ctx.runMutation(internal.ingest.deadLetter, { record: await body(request) }), 202); } catch { return error(422, "VALIDATION_FAILED", "Invalid dead-letter payload"); } }));

route("/runtime/claim", "POST", httpAction(async (ctx, request) => {
  if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token");
  try { const input = await body(request); const leaseToken = `${crypto.randomUUID()}${crypto.randomUUID()}`; const claimed = await ctx.runMutation(internal.tasks.claim, { ownerId: input.ownerId, leaseMs: input.leaseMs ?? 60_000, leaseTokenHash: await sha256(leaseToken), now: Date.now() }); if (!claimed) return json({ task: null }, 200); const repository = await ctx.runQuery(internal.repositories.getRedacted, { repo: claimed.repo }); const memoryPack = domainProjection(await ctx.runQuery(internal.memory.pack, { repo: claimed.repo, now: Date.now(), limit: 50 })); return json({ task: runtimeTask(claimed, repository, memoryPack), leaseId: `lse_${crypto.randomUUID().replaceAll("-", "")}`, leaseToken, expiresAt: new Date(claimed.leaseExpiresAt).toISOString() }); } catch { return error(422, "VALIDATION_FAILED", "Invalid claim request"); }
}));
route("/runtime/heartbeat", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const result = await ctx.runMutation(internal.tasks.heartbeat, { taskId: input.taskId, ownerId: input.ownerId, leaseTokenHash: await sha256(input.leaseToken), extensionMs: input.extensionMs ?? 60_000, now: Date.now() }); return result.ok ? json(result) : error(409, result.reason ?? "LOST_LEASE", "Lease is no longer current"); } catch { return error(422, "VALIDATION_FAILED", "Invalid heartbeat request"); } }));
route("/runtime/run/start", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const leaseToken = input.leaseToken; const run = { ...input }; delete run.leaseToken; const result = await ctx.runMutation(internal.runtime.startRun, { run, leaseTokenHash: await sha256(leaseToken), now: Date.now() }); return result.ok ? json(result, 202) : error(409, result.reason ?? "RUN_START_REJECTED", "Run start rejected"); } catch { return error(422, "VALIDATION_FAILED", "Invalid run"); } }));
route("/runtime/run/resume", "GET", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); const runId = new URL(request.url).searchParams.get("runId") ?? ""; if (!/^run_[0-9A-HJKMNP-TV-Z]{26}$/.test(runId)) return error(422, "VALIDATION_FAILED", "A valid run ID is required"); const state = await ctx.runQuery(internal.runtime.resumeState, { runId }); if (!state) return error(404, "RUN_NOT_FOUND", "Run does not exist"); return state.resumable ? json(state) : error(409, "RUN_NOT_RESUMABLE", "Only an interrupted running run can resume"); }));
route("/runtime/event", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); if (!input.runId || !input.taskId || !input.eventId || !Number.isInteger(input.sequence)) return error(422, "VALIDATION_FAILED", "Invalid runtime event"); const event = { eventId: input.eventId, runId: input.runId, taskId: input.taskId, sequence: input.sequence, kind: input.type, label: input.label ?? "live", projectionRedacted: { type: input.type, source: input.source, spanId: input.spanId, payload: input.payload, redactionLevel: input.redactionLevel }, createdAt: Date.parse(input.timestamp) || Date.now() }; const result = await ctx.runMutation(internal.runtime.appendEvent, { event }); return result.conflict ? error(409, "SEQUENCE_CONFLICT", `Expected sequence ${result.expectedSequence}`) : json(result, 202); } catch { return error(422, "VALIDATION_FAILED", "Invalid runtime event"); } }));
route("/runtime/span", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const now = Date.now(); const span = { spanId: input.spanId, eventId: `span:${input.spanId}`, sequence: 0, runId: input.runId, taskId: input.taskId, nodeId: input.nodeId, agent: input.agent, agentVersion: input.agentVersion ?? "1.0", model: input.model ?? "deterministic", baseRevision: "local", baseSha256: "0".repeat(64), quantization: "unknown", promptHash: input.promptHash || "0".repeat(64), inputArtifactRefs: input.inputArtifactRefs ?? [], tokensIn: input.tokensIn ?? 0, tokensOut: input.tokensOut ?? 0, costUsd: input.costUsd ?? 0, costCloudEquivalentUsd: input.costCloudEquivUsd ?? 0, latencyMs: Math.round(input.latencyMs ?? 0), toolCalls: input.toolCalls ?? [], executionLocation: "local_cpu", fallback: Boolean(input.degraded), status: input.error ? "failed" : "succeeded", startedAt: Math.max(0, now - Math.round(input.latencyMs ?? 0)), finishedAt: now, ...(input.parentSpanId ? { parentSpanId: input.parentSpanId } : {}), ...(input.outputArtifactRef ? { outputArtifactRef: input.outputArtifactRef } : {}), ...(input.verdict ? { verdict: input.verdict } : {}), ...(input.error ? { error: { code: "RUNTIME_NODE_FAILED", message: String(input.error).slice(0, 2_048), retryable: false } } : {}) }; return json(await ctx.runMutation(internal.runtime.putSpan, { span }), 202); } catch { return error(422, "VALIDATION_FAILED", "Invalid span"); } }));
route("/runtime/artifact", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request, 4_500_000); const content = typeof input.content === "string" ? input.content : canonicalJson(input.content ?? {}); JSON.parse(content); if (await sha256(content) !== input.contentHash) return error(422, "ARTIFACT_HASH_MISMATCH", "Artifact content hash is invalid"); if (containsSecretLikeMaterial(content)) return error(422, "RAW_SECRET_REJECTED", "Artifact contains secret-like material"); const restrictedTypes = new Set(["secret_finding", "security_report", "sarif_report", "remediation_plan"]); const restricted = restrictedTypes.has(input.artifactType); const artifact = { artifactId: input.artifactId, schemaVersion: 1, taskId: input.taskId, runId: input.runId, nodeId: `node_${String(input.producer ?? "runtime").replace(/[^A-Za-z0-9_-]/g, "_")}`, type: input.artifactType, producer: { name: input.producer, version: input.producerVersion ?? "1.0" }, upstreamArtifactIds: input.upstreamArtifactIds ?? [], policyRuleIds: input.policyIds ?? [], contentHash: input.contentHash, contentRedacted: content, searchableProjection: restricted ? "[restricted security artifact]" : content.slice(0, 8_192), retentionClass: restricted ? "restricted" : "standard", createdAt: Date.parse(input.createdAt) || Date.now() }; const stored = await ctx.runMutation(internal.runtime.putArtifact, { artifact }); return stored.conflict ? error(409, "ARTIFACT_ID_COLLISION", "Artifact ID already exists with different content") : json(stored, 202); } catch (cause) { return cause instanceof RangeError ? error(413, "TOO_LARGE", "Artifact exceeds limit") : error(422, "VALIDATION_FAILED", "Invalid artifact"); } }));
route("/runtime/run/finish", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const result = await ctx.runMutation(internal.runtime.finalizeRun, { taskId: input.taskId, ownerId: input.ownerId, leaseTokenHash: await sha256(input.leaseToken), taskStatus: input.taskStatus, resultUrls: input.resultUrls ?? [], error: input.error, runId: input.runId, runPatch: input.run, now: Date.now() }); return result.ok ? json(result) : error(result.reason === "LOST_LEASE" ? 409 : 422, result.reason ?? "RUN_FINISH_REJECTED", "Run completion rejected"); } catch { return error(422, "VALIDATION_FAILED", "Invalid finish request"); } }));
route("/runtime/task/escalate", "POST", httpAction(async (ctx, request) => {
  if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token");
  try {
    const input = await body(request);
    const artifactIds = input.artifactIds ?? [];
    const resultUrls = input.resultUrls ?? [];
    const suppliedError = input.error;
    const validError = suppliedError === undefined || (
      suppliedError && typeof suppliedError === "object" && !Array.isArray(suppliedError)
      && typeof suppliedError.code === "string" && suppliedError.code.length >= 1 && suppliedError.code.length <= 64
      && typeof suppliedError.message === "string" && suppliedError.message.length >= 1 && suppliedError.message.length <= 2_048
      && suppliedError.retryable === false
      && Object.keys(suppliedError).every((key) => ["code", "message", "retryable"].includes(key))
    );
    const reason = String(input.reason ?? suppliedError?.message ?? "Runtime requested human review").slice(0, 4_096);
    const secretLike = containsSecretLikeMaterial(reason) || (validError && suppliedError ? containsSecretLikeMaterial(suppliedError.message) : false);
    if (typeof input.taskId !== "string" || input.taskId.length > 128 || typeof input.ownerId !== "string" || input.ownerId.length < 1 || input.ownerId.length > 256 || typeof input.leaseToken !== "string" || input.leaseToken.length < 32 || input.leaseToken.length > 256 || (input.runId !== undefined && (typeof input.runId !== "string" || input.runId.length > 128)) || (input.reason !== undefined && (typeof input.reason !== "string" || input.reason.length > 4_096)) || (input.restricted !== undefined && typeof input.restricted !== "boolean") || !validError || !Array.isArray(artifactIds) || artifactIds.length > 100 || artifactIds.some((value: unknown) => typeof value !== "string" || value.length > 128) || !Array.isArray(resultUrls) || resultUrls.some((value: unknown) => !isSafeHttpsUrl(value)) || secretLike) return error(422, secretLike ? "RAW_SECRET_REJECTED" : "VALIDATION_FAILED", "Invalid escalation request");
    const result = await ctx.runMutation(internal.tasks.escalate, {
      taskId: input.taskId,
      ownerId: input.ownerId,
      leaseTokenHash: await sha256(input.leaseToken),
      ...(typeof input.runId === "string" ? { runId: input.runId } : {}),
      artifactIds,
      resultUrls,
      error: input.error,
      reason,
      restricted: input.restricted === true,
      reviewItemId: newDomainId("rvi"),
      now: Date.now(),
    });
    return result.ok ? json(result) : error(result.reason === "LOST_LEASE" ? 409 : 422, result.reason ?? "ESCALATION_REJECTED", "Escalation rejected");
  } catch (cause) {
    return cause instanceof RangeError ? error(413, "TOO_LARGE", "Escalation exceeds limit") : error(422, "VALIDATION_FAILED", "Invalid escalation request");
  }
}));
route("/runtime/security/findings", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const now = Date.now(); const lease = await ctx.runMutation(internal.tasks.heartbeat, { taskId: input.taskId, ownerId: input.ownerId, leaseTokenHash: await sha256(input.leaseToken), extensionMs: 60_000, now }); if (!lease.ok) return error(409, lease.reason ?? "LOST_LEASE", "Finding lease is no longer current"); const task = await ctx.runQuery(internal.tasks.getByTaskId, { taskId: input.taskId }); if (!task || input.finding?.taskId !== input.taskId || input.finding?.repo !== task.repo) return error(422, "FINDING_SCOPE_MISMATCH", "Finding does not belong to the leased task"); const result = await ctx.runMutation(internal.security.upsertFinding, { finding: input.finding, now }); return result.ok ? json(result, 202) : error(422, result.reason ?? "FINDING_REJECTED", "Finding rejected"); } catch { return error(422, "VALIDATION_FAILED", "Invalid finding"); } }));
route("/runtime/control", "GET", httpAction(async (ctx, request) => authorized(request, "CONTROL_PLANE_INGEST_TOKEN") ? json(domainProjection(await ctx.runQuery(internal.controls.get, {}))) : error(401, "UNAUTHENTICATED", "Invalid bearer token")));
route("/runtime/config/agents", "GET", httpAction(async (ctx, request) => authorized(request, "CONTROL_PLANE_INGEST_TOKEN") ? json(domainProjection({ agents: await ctx.runQuery(internal.agents.listActive, {}), adapters: await ctx.runQuery(internal.adapters.activePointers, {}) })) : error(401, "UNAUTHENTICATED", "Invalid bearer token")));

route("/providers/authorize", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); return json(await ctx.runQuery(internal.providers.authorize, { taskId: input.taskId, repo: input.repo, purpose: input.purpose, requestedProvider: input.requestedProvider, now: Date.now() })); } catch { return error(422, "VALIDATION_FAILED", "Invalid authorization request"); } }));
route("/providers/audit", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const usage = input.tokens ?? {}; const call = { providerCallId: newDomainId("prc"), taskId: input.taskId, repo: input.repo, provider: input.provider, model: input.exactModel ?? input.model ?? "unknown", purpose: input.purpose, consentRef: input.consentRef, classification: input.classification, bytesSent: input.bytesSent, tokensIn: input.tokensIn ?? usage.prompt_tokens ?? 0, tokensOut: input.tokensOut ?? usage.completion_tokens ?? 0, latencyMs: input.latencyMs ?? 0, costUsd: input.costUsd ?? 0, executionLocation: input.executionLocation ?? "remote_provider", requestId: input.requestId, status: input.status ?? "completed", createdAt: input.createdAt ?? Date.now() }; return json(await ctx.runMutation(internal.providers.record, { call }), 202); } catch { return error(422, "VALIDATION_FAILED", "Invalid provider audit"); } }));
route("/writeback/reserve", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request, 2_500_000); const result = await ctx.runMutation(internal.writeback.reserve, { intent: input.intent, leaseTokenHash: await sha256(input.leaseToken), now: Date.now() }); if (result.ok || result.reason === "DRY_RUN") return json(result); return error(result.reason === "LOST_LEASE" || result.reason === "IN_PROGRESS" ? 409 : 403, result.reason ?? "DENIED", "Write-back authorization denied"); } catch (cause) { return cause instanceof RangeError ? error(413, "TOO_LARGE", "Write-back exceeds limit") : error(422, "VALIDATION_FAILED", "Invalid write-back"); } }));
route("/writeback/complete", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); const result = await ctx.runMutation(internal.writeback.complete, { ...input, now: Date.now() }); return result.ok ? json(result) : error(409, result.reason ?? "COMPLETION_REJECTED", "Write-back completion rejected"); } catch { return error(422, "VALIDATION_FAILED", "Invalid completion"); } }));
route("/writeback/fail", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const input = await body(request); return json(await ctx.runMutation(internal.writeback.fail, { writebackId: input.writebackId, error: input.error, now: Date.now() })); } catch { return error(422, "VALIDATION_FAILED", "Invalid failure record"); } }));
route("/maintenance/retry-dead-letters", "POST", httpAction(async (ctx, request) => {
  if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token");
  const now = Date.now();
  const due = await ctx.runQuery(internal.ingest.dueDeadLetters, { now, limit: 25 });
  const results = [];
  for (const item of due) results.push(await ctx.runMutation(internal.ingest.retryOne, { deliveryId: item.deliveryId, taskId: newDomainId("tsk"), now }));
  return json({ attempted: due.length, recovered: results.filter((result) => result.ok).length }, 202);
}));
route("/admin/repositories/upsert", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { const repository = await body(request); return json({ id: await ctx.runMutation(internal.repositories.upsert, { repository: { ...repository, updatedAt: Date.now() } }) }); } catch { return error(422, "VALIDATION_FAILED", "Invalid repository descriptor"); } }));
route("/admin/control", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "CONTROL_PLANE_INGEST_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid bearer token"); try { return json(await ctx.runMutation(internal.controls.update, { patch: await body(request), now: Date.now() })); } catch { return error(422, "VALIDATION_FAILED", "Invalid control state"); } }));

route("/gateway/task-drafts", "POST", httpAction(async (ctx, request) => { if (!authorized(request, "GATEWAY_BEARER_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid gateway bearer token"); try { const draft = await body(request, 32_768); const idempotencyKey = request.headers.get("Idempotency-Key") ?? ""; if (idempotencyKey.length < 16 || idempotencyKey.length > 256) return error(422, "VALIDATION_FAILED", "A valid idempotency key is required"); const result = await ctx.runMutation(internal.gateway.createTaskDraft, { draft, idempotencyKey, taskId: newDomainId("tsk"), now: Date.now() }); return result.ok ? json({ taskId: result.taskId, duplicate: result.duplicate }) : error(result.reason === "REPOSITORY_NOT_ALLOWLISTED" ? 403 : 422, result.reason ?? "TASK_REJECTED", result.reason === "GITHUB_URL_REQUIRED" ? "Prompt must contain an allowlisted GitHub repository, issue, or pull request URL" : "Task draft was rejected"); } catch (cause) { return cause instanceof RangeError ? error(413, "TOO_LARGE", "Task draft exceeds limit") : error(422, "VALIDATION_FAILED", "Invalid task draft"); } }));
route("/gateway/events", "GET", httpAction(async (ctx, request) => { if (!authorized(request, "GATEWAY_BEARER_TOKEN")) return error(401, "UNAUTHENTICATED", "Invalid gateway bearer token"); const url = new URL(request.url); const events = await ctx.runQuery(internal.gateway.eventsAfter, { after: url.searchParams.get("after") || undefined, limit: 500 }); return json(events.map(gatewayEvent)); }));
route("/gateway/status", "GET", httpAction(async (ctx, request) => authorized(request, "GATEWAY_BEARER_TOKEN") ? json(await ctx.runQuery(internal.gateway.statuses, {})) : error(401, "UNAUTHENTICATED", "Invalid gateway bearer token")));

export default http;
