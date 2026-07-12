import { describe, expect, test } from "bun:test";
import { isHermesAuthored, normalizeGitHubWebhook } from "../apps/worker/src/normalize";
import { verifyGitHubSignature } from "../apps/worker/src/signature";

async function signature(body: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const digest = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return `sha256=${[...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

describe("GitHub webhook boundary", () => {
  test("valid raw-body HMAC succeeds", async () => { const raw = "{\"action\":\"opened\"}"; expect(await verifyGitHubSignature(new TextEncoder().encode(raw).buffer, await signature(raw, "webhook-secret"), "webhook-secret")).toBeTrue(); });
  test("invalid and missing signatures fail", async () => { const raw = new TextEncoder().encode("{}").buffer; expect(await verifyGitHubSignature(raw, null, "secret")).toBeFalse(); expect(await verifyGitHubSignature(raw, `sha256=${"0".repeat(64)}`, "secret")).toBeFalse(); });
  test("Hermes marker suppresses loops regardless of actor", () => expect(isHermesAuthored({ sender: { login: "someone" }, comment: { body: "ok\n<!-- hermes:writeback -->" } }, "hermes-bot")).toBeTrue());
  test("Hermes bot identity suppresses loops", () => expect(isHermesAuthored({ sender: { login: "Hermes-Bot", type: "Bot" } }, "hermes-bot")).toBeTrue());
  test("issues normalize into repository-scoped maintainer tasks", async () => { const normalized = await normalizeGitHubWebhook("issues", "delivery-1", { action: "opened", repository: { full_name: "desync-organization/helios", private: false, id: 7, html_url: "https://github.com/desync-organization/helios" }, sender: { login: "contributor" }, issue: { number: 12, title: "Bug", body: "Something broke", html_url: "https://github.com/desync-organization/helios/issues/12" } }); expect(normalized?.mode).toBe("maintain"); expect(normalized?.type).toBe("intake"); expect(normalized?.dedupeKey).toContain("desync-organization/helios"); });
  test("security events normalize into defensive audit tasks", async () => { const normalized = await normalizeGitHubWebhook("secret_scanning_alert", "delivery-2", { action: "created", repository: { full_name: "desync-organization/helios", private: true }, sender: { login: "github" }, alert: { number: 3, state: "open" } }); expect(normalized?.mode).toBe("security_audit"); expect(normalized?.type).toBe("secret_scan"); expect(normalized?.dataClassification).toBe("private"); });
  test("secret-like webhook content is redacted", async () => { const normalized = await normalizeGitHubWebhook("issues", "delivery-3", { action: "opened", repository: { full_name: "desync-organization/helios", private: false }, sender: { login: "user" }, issue: { number: 1, body: "token=abcdefghijklmnopqrstuvwxyz123456" } }); expect(normalized?.payloadRedacted).toContain("[REDACTED:credential_assignment]"); expect(normalized?.payloadRedacted).not.toContain("abcdefghijklmnopqrstuvwxyz123456"); });
  test("unsupported events do not enqueue", async () => expect(await normalizeGitHubWebhook("push", "delivery", { repository: { full_name: "a/b" } })).toBeNull());
});
