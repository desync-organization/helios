import { z } from "zod";
import { BodyText, EpochMs, RetentionClass, Sha256, ShortText, externalObject } from "./common";
import { ArtifactId, RunId, TaskId } from "./ids";

export const ArtifactType = z.enum([
  "plan", "classification", "dup_report", "research", "repro_report", "patch", "test_result", "security_report", "review_notes",
  "draft_reply", "critic_verdict", "blocked", "escalation", "release_draft", "requirements_spec", "architecture_decision",
  "implementation_plan", "build_manifest", "package_result", "deployment_draft", "repository_inventory", "dependency_inventory",
  "sbom", "secret_finding", "vulnerability_finding", "threat_model", "remediation_plan", "sarif_report",
]);

export const ArtifactProducer = z.object({ name: ShortText, version: ShortText }).strict();
export const Artifact = externalObject({
  artifactId: ArtifactId,
  taskId: TaskId,
  runId: RunId,
  nodeId: z.string().regex(/^node_[A-Za-z0-9_-]{1,80}$/),
  type: ArtifactType,
  producer: ArtifactProducer,
  upstreamArtifactIds: z.array(ArtifactId).max(200),
  policyRuleIds: z.array(z.string().min(1).max(128)).max(100),
  contentHash: Sha256,
  content: BodyText,
  retentionClass: RetentionClass,
  createdAt: EpochMs,
});

export const CriticVerdict = z.object({
  verdict: z.enum(["pass", "revise", "blocked"]),
  reviewedArtifactId: ArtifactId,
  reviewedContentHash: Sha256,
  producerAgent: ShortText,
  criticAgent: ShortText,
  criteria: z.array(z.object({ criterion: z.string().min(1).max(1_024), passed: z.boolean(), note: z.string().max(2_048) }).strict()).min(1).max(100),
  targetNodeId: z.string().max(96).optional(),
  rejectionFingerprint: Sha256.optional(),
}).strict().refine((value) => value.producerAgent !== value.criticAgent, "critic must be independent");

export type ArtifactType = z.infer<typeof ArtifactType>;
export type Artifact = z.infer<typeof Artifact>;
export type CriticVerdict = z.infer<typeof CriticVerdict>;
