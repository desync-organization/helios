import { describe, expect, test } from "bun:test";
import { EgressController, type ProviderAdapter } from "../src/providers/egress";
import { assertNoRawSecrets, containsSuspectedSecret, redactSensitive } from "../src/security/redaction";
import { repository, task } from "./fixtures";

class Provider implements ProviderAdapter {
  received = "";
  async invoke(request: any) { this.received = request.content; return { provider: request.provider, model: "model", output: "ok", tokensIn: 3, tokensOut: 1, latencyMs: 10, costUsd: 0.01, requestId: "request-1" }; }
}

describe("privacy and provider consent", () => {
  test("known token forms are detected and redacted", async () => { const input = `authorization: Bearer github_pat_${"A".repeat(30)}`; expect(containsSuspectedSecret(input)).toBeTrue(); const result = await redactSensitive(input); expect(result.value).not.toContain("github_pat_"); expect(result.findings.length).toBeGreaterThan(0); });
  test("raw secret boundary rejects secret-like content", () => expect(() => assertNoRawSecrets(`ghp_${"a".repeat(30)}`)).toThrow());
  test("private local-only tasks cannot call hosted providers", async () => { const provider = new Provider(); const controller = new EgressController({ workers_ai: provider }); const t = task({ dataClassification: "private", consentScope: { ...task().consentScope, privateCodeMayLeaveDevice: false } }); await expect(controller.invoke({ taskId: t.taskId, repo: t.repo, purpose: "triage", provider: "workers_ai", content: "private code", classification: "private", consent: t.consentScope }, repository({ visibility: "private" }), 2_000)).rejects.toThrow("local-only"); expect(provider.received).toBe(""); });
  test("provider payload is redacted and egress is audited", async () => { const provider = new Provider(); const controller = new EgressController({ workers_ai: provider }); const t = task(); await controller.invoke({ taskId: t.taskId, repo: t.repo, purpose: "triage", provider: "workers_ai", content: `token=${"z".repeat(30)}`, classification: "public", consent: t.consentScope }, repository(), 2_000); expect(provider.received).toContain("[REDACTED:credential_assignment]"); expect(controller.audit).toHaveLength(1); expect(controller.audit[0].costUsd).toBe(0.01); });
  test("external vulnerability intelligence requires separate consent", async () => { const controller = new EgressController({ linkup: new Provider() }); const t = task(); await expect(controller.invoke({ taskId: t.taskId, repo: t.repo, purpose: "vulnerability_intelligence", provider: "linkup", content: "CVE lookup", classification: "public", consent: t.consentScope }, repository(), 2_000)).rejects.toThrow("security upload"); });
});
