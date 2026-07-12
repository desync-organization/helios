import { z } from "zod";
import { EpochMs, GitSha, Sha256, ShortText, externalObject } from "./common";
import { ArtifactId, RunId, TaskId } from "./ids";
import { RepoSlug } from "./repository";

export const BuildManifest = externalObject({
  taskId: TaskId,
  runId: RunId,
  repo: RepoSlug,
  baseSha: GitSha,
  files: z.array(z.object({ path: z.string().min(1).max(512), sha256: Sha256, bytes: z.number().int().nonnegative() }).strict()).min(1).max(2_000),
  requirementsArtifactId: ArtifactId,
  architectureArtifactId: ArtifactId,
  testArtifactIds: z.array(ArtifactId).min(1).max(100),
  securityArtifactIds: z.array(ArtifactId).min(1).max(100),
  buildCommands: z.array(ShortText).max(100),
  createdAt: EpochMs,
});

export type BuildManifest = z.infer<typeof BuildManifest>;
