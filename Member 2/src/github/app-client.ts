import { SignJWT, importPKCS8 } from "jose";
import type { WritebackIntent, BranchPrPayload } from "../../packages/contracts/src/writeback";
import { ControlPlaneError } from "../errors";
import type { GitHubExecutionContext, GitHubExecutor } from "./writeback-service";

interface GitHubAppConfig { appId: string; privateKeyPem: string; apiBaseUrl?: string; userAgent?: string }
interface GitHubResponse<T> { data: T; status: number }

export class GitHubAppClient implements GitHubExecutor {
  private readonly apiBaseUrl: string;
  constructor(private readonly config: GitHubAppConfig, private readonly fetcher: typeof fetch = fetch) {
    this.apiBaseUrl = config.apiBaseUrl ?? "https://api.github.com";
  }

  private async appJwt(now = Math.floor(Date.now() / 1000)): Promise<string> {
    const key = await importPKCS8(this.config.privateKeyPem.replace(/\\n/g, "\n"), "RS256");
    return new SignJWT({}).setProtectedHeader({ alg: "RS256" }).setIssuer(this.config.appId).setIssuedAt(now - 30).setExpirationTime(now + 540).sign(key);
  }

  private async installationToken(installationId: number): Promise<string> {
    const response = await this.request<{ token: string }>(`/app/installations/${installationId}/access_tokens`, { method: "POST", token: await this.appJwt() });
    return response.data.token;
  }

  private async request<T>(path: string, options: { method?: string; token: string; body?: unknown }): Promise<GitHubResponse<T>> {
    const response = await this.fetcher(`${this.apiBaseUrl}${path}`, {
      method: options.method ?? "GET",
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${options.token}`, "Content-Type": "application/json", "User-Agent": this.config.userAgent ?? "Hermes-Control-Plane/2.0", "X-GitHub-Api-Version": "2022-11-28" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    if (!response.ok) throw new ControlPlaneError("UPSTREAM_FAILED", `GitHub request failed with status ${response.status}`, response.status >= 500 ? 502 : 409, response.status >= 500);
    return { data: await response.json() as T, status: response.status };
  }

  async execute(intent: WritebackIntent, context: GitHubExecutionContext): Promise<{ resultUrl: string; externalId: string }> {
    const token = await this.installationToken(context.installationId);
    const [owner, repo] = intent.repo.split("/");
    const issuePath = `/repos/${owner}/${repo}/issues`;
    switch (intent.payload.action) {
      case "comment":
      case "build_status_comment": {
        const result = await this.request<{ html_url: string; id: number }>(`${issuePath}/${intent.payload.data.issueNumber}/comments`, { method: "POST", token, body: { body: `${intent.payload.data.body}\n\n<!-- hermes:writeback -->` } });
        return { resultUrl: result.data.html_url, externalId: String(result.data.id) };
      }
      case "labels_set": {
        const result = await this.request<{ html_url: string; id: number }>(`${issuePath}/${intent.payload.data.issueNumber}`, { method: "PATCH", token, body: { labels: intent.payload.data.labels } });
        return { resultUrl: result.data.html_url, externalId: String(result.data.id) };
      }
      case "milestone_set": {
        const result = await this.request<{ html_url: string; id: number }>(`${issuePath}/${intent.payload.data.issueNumber}`, { method: "PATCH", token, body: { milestone: intent.payload.data.milestoneNumber } });
        return { resultUrl: result.data.html_url, externalId: String(result.data.id) };
      }
      case "duplicate_close": {
        await this.request(`${issuePath}/${intent.payload.data.issueNumber}/comments`, { method: "POST", token, body: { body: `${intent.payload.data.comment}\n\nDuplicate of #${intent.payload.data.duplicateOf}.\n\n<!-- hermes:writeback -->` } });
        const result = await this.request<{ html_url: string; id: number }>(`${issuePath}/${intent.payload.data.issueNumber}`, { method: "PATCH", token, body: { state: "closed", state_reason: "not_planned" } });
        return { resultUrl: result.data.html_url, externalId: String(result.data.id) };
      }
      case "branch_and_pr":
      case "build_branch_and_pr":
      case "security_pr":
      case "policy_commit":
      case "eval_case_commit":
        return this.createPullRequest(owner, repo, token, intent.payload.data, intent.baseSha!, context.defaultBranch);
      case "pr_review_comment": {
        const data = intent.payload.data;
        const result = await this.request<{ html_url: string; id: number }>(`/repos/${owner}/${repo}/pulls/${data.pullNumber}/comments`, { method: "POST", token, body: { body: data.body, commit_id: data.commitId, path: data.path, line: data.line, side: "RIGHT" } });
        return { resultUrl: result.data.html_url, externalId: String(result.data.id) };
      }
      case "pr_merge": {
        const data = intent.payload.data;
        const result = await this.request<{ sha: string; merged: boolean }>(`/repos/${owner}/${repo}/pulls/${data.pullNumber}/merge`, { method: "PUT", token, body: { sha: data.expectedHeadSha, merge_method: data.method } });
        if (!result.data.merged) throw new ControlPlaneError("CONFLICT", "GitHub declined the merge", 409, false);
        return { resultUrl: `https://github.com/${owner}/${repo}/pull/${data.pullNumber}`, externalId: result.data.sha };
      }
      case "release_draft": {
        const data = intent.payload.data;
        const result = await this.request<{ html_url: string; id: number }>(`/repos/${owner}/${repo}/releases`, { method: "POST", token, body: { tag_name: data.tagName, name: data.name, body: data.body, target_commitish: data.targetCommitish, draft: true, prerelease: false } });
        return { resultUrl: result.data.html_url, externalId: String(result.data.id) };
      }
      case "sarif_upload": {
        const data = intent.payload.data;
        const result = await this.request<{ id: string; url: string }>(`/repos/${owner}/${repo}/code-scanning/sarifs`, { method: "POST", token, body: { commit_sha: data.commitSha, ref: data.ref, sarif: data.sarifGzipBase64 } });
        return { resultUrl: result.data.url.startsWith("https://") ? result.data.url : `https://github.com/${owner}/${repo}/security/code-scanning`, externalId: result.data.id };
      }
      case "security_issue_draft":
        throw new ControlPlaneError("POLICY_DENIED", "Public security issue creation is disabled", 403, false);
    }
  }

  private async createPullRequest(owner: string, repo: string, token: string, payload: BranchPrPayload, baseSha: string, defaultBranch: string): Promise<{ resultUrl: string; externalId: string }> {
    if (!baseSha) throw new ControlPlaneError("VALIDATION_FAILED", "A base SHA is required for patch write-back", 422, false);
    const currentRef = await this.request<{ object: { sha: string } }>(`/repos/${owner}/${repo}/git/ref/heads/${encodeURIComponent(defaultBranch)}`, { token });
    if (currentRef.data.object.sha !== baseSha) throw new ControlPlaneError("CONFLICT", "Repository base branch changed after artifact production", 409, false);
    const baseCommit = await this.request<{ tree: { sha: string } }>(`/repos/${owner}/${repo}/git/commits/${baseSha}`, { token });
    const treeItems: Array<{ path: string; mode: "100644"; type: "blob"; sha: string }> = [];
    for (const file of payload.files) {
      const blob = await this.request<{ sha: string }>(`/repos/${owner}/${repo}/git/blobs`, { method: "POST", token, body: { content: file.content, encoding: "utf-8" } });
      treeItems.push({ path: file.path, mode: "100644", type: "blob", sha: blob.data.sha });
    }
    const tree = await this.request<{ sha: string }>(`/repos/${owner}/${repo}/git/trees`, { method: "POST", token, body: { base_tree: baseCommit.data.tree.sha, tree: treeItems } });
    const commit = await this.request<{ sha: string }>(`/repos/${owner}/${repo}/git/commits`, { method: "POST", token, body: { message: payload.title, tree: tree.data.sha, parents: [baseSha] } });
    await this.request(`/repos/${owner}/${repo}/git/refs`, { method: "POST", token, body: { ref: `refs/heads/${payload.branch}`, sha: commit.data.sha } });
    const pull = await this.request<{ html_url: string; number: number }>(`/repos/${owner}/${repo}/pulls`, { method: "POST", token, body: { title: payload.title, body: payload.body, head: payload.branch, base: defaultBranch, draft: payload.draft } });
    return { resultUrl: pull.data.html_url, externalId: String(pull.data.number) };
  }
}
