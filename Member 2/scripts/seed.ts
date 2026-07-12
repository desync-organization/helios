import { controlPost, required } from "./env";

const repo = required("DEMO_REPOSITORY");
const now = Date.now();
const repository = {
  repo,
  githubRepositoryId: required("DEMO_GITHUB_REPOSITORY_ID"),
  installationId: required("DEMO_GITHUB_INSTALLATION_ID"),
  defaultBranch: "main",
  visibility: "public",
  writebackOptIn: true,
  securityAuditOptIn: true,
  allowedActions: ["comment", "labels_set", "milestone_set", "duplicate_close", "branch_and_pr", "pr_review_comment", "release_draft", "security_pr", "build_branch_and_pr", "build_status_comment"],
  allowedCloudProviders: [],
  protectedPaths: [".github/workflows/**", ".github/CODEOWNERS", "policy/production/**"],
  sizeLimits: { maxPatchBytes: 100_000, maxFiles: 20 },
  requiredChecks: ["member-2-control-plane"],
  activePolicyVersion: "2.0.0",
  retentionPolicy: { artifactDays: 90, entityDays: 30, providerPayloadHours: 0, voiceAudioMinutes: 0, scannerOutputHours: 24 },
  health: "healthy",
  updatedAt: now,
};
await controlPost("/admin/repositories/upsert", repository);
await controlPost("/admin/control", { globalPaused: false, emergencyMode: false, pausedAgents: [], writebackMode: "dry-run", securityScanMode: "read-only", currentAgentTag: "agents-v1", currentAdapterPointers: {} });
console.log(`Seeded ${repo} in dry-run/read-only mode. No external mutation was performed.`);
