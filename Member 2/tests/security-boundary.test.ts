import { describe, expect, test } from "bun:test";

const root = new URL("../../", import.meta.url);
async function source(path: string): Promise<string> { return Bun.file(new URL(path, root)).text(); }

describe("existing server API hardening", () => {
  test("GitHub API route rejects browser PAT storage", async () => { const text = await source("src/app/api/auth/github/route.ts"); expect(text).not.toContain("writeFile"); expect(text).not.toContain("GITHUB_TOKEN"); expect(text).toContain("GITHUB_APP_REQUIRED"); });
  test("Vercel API route rejects browser token storage", async () => { const text = await source("src/app/api/auth/vercel/route.ts"); expect(text).not.toContain("writeFile"); expect(text).not.toContain("VERCEL_TOKEN"); expect(text).toContain("SERVER_MANAGED_CREDENTIAL"); });
  test("auth status never reads credential files", async () => { const text = await source("src/app/api/auth/status/route.ts"); expect(text).not.toContain("readFile"); expect(text).toContain("browserTokenStorageEnabled: false"); });
  test("local git API contains no mutation commands", async () => { const text = await source("src/app/api/git/route.ts"); expect(text).not.toContain('"merge"'); expect(text).not.toContain('"-D"'); expect(text).not.toContain('"checkout"'); expect(text).toContain("READ_ONLY_COMMANDS"); });
  test("runtime projections strip Convex and credential IDs", async () => { const text = await source("Member 2/convex/http.ts"); expect(text).toContain('"_id"'); expect(text).toContain('"_creationTime"'); expect(text).toContain('"installationId"'); expect(text).toContain("domainProjection(claimed)"); });
  test("sensitive Convex modules expose internal functions only", async () => { const modules = ["tasks", "repositories", "ingest", "runtime", "security", "controls", "providers", "memory", "adapters", "writeback", "agents", "alerts", "evals", "policies", "backlog"]; for (const module of modules) { const text = await source(`Member 2/convex/${module}.ts`); expect(text).not.toMatch(/\bexport const \w+ = (?:mutation|query)\(/); } });
});
