import { z } from "zod";
import { EpochMs, GitSha, HttpsUrl, Sha256, ShortText, externalObject } from "./common";
import { FindingId, ScanId } from "./ids";
import { RepoSlug } from "./repository";

export const Severity = z.enum(["info", "low", "medium", "high", "critical"]);
export const Confidence = z.enum(["low", "medium", "high", "confirmed"]);
export const FindingStatus = z.enum(["open", "triaged", "false_positive", "remediation_planned", "fixed", "accepted_risk"]);
export const VulnerabilityFinding = externalObject({
  findingId: FindingId,
  scanner: ShortText,
  scannerVersion: ShortText,
  ruleId: ShortText,
  category: z.enum(["dependency", "secret", "sast", "configuration", "supply_chain"]),
  severity: Severity,
  confidence: Confidence,
  cwe: z.string().regex(/^CWE-\d+$/).optional(),
  cve: z.string().regex(/^CVE-\d{4}-\d{4,}$/).optional(),
  advisoryUrls: z.array(HttpsUrl).max(20),
  advisoryRetrievedAt: EpochMs.optional(),
  repo: RepoSlug,
  commitSha: GitSha,
  path: z.string().min(1).max(512).optional(),
  startLine: z.number().int().positive().optional(),
  endLine: z.number().int().positive().optional(),
  evidenceRedacted: z.string().min(1).max(8_192),
  evidenceFingerprint: Sha256,
  exploitability: z.enum(["none", "theoretical", "conditional", "likely", "demonstrated_safe_fixture"]),
  reachability: z.enum(["unknown", "unreachable", "potentially_reachable", "reachable"]),
  falsePositiveReason: z.string().max(2_048).optional(),
  recommendedFix: z.string().min(1).max(8_192),
  status: FindingStatus,
});

export const SecretFinding = externalObject({
  findingId: FindingId,
  repo: RepoSlug,
  commitSha: GitSha,
  detector: ShortText,
  secretType: ShortText,
  path: z.string().min(1).max(512),
  line: z.number().int().positive().optional(),
  fingerprint: Sha256,
  redactedPrefix: z.string().max(4).optional(),
  redactedSuffix: z.string().max(4).optional(),
  rotationRecommended: z.boolean(),
  remediationState: FindingStatus,
});

export const ScanRun = externalObject({
  scanId: ScanId,
  repo: RepoSlug,
  commitSha: GitSha,
  kind: z.enum(["dependency", "secret", "sast", "config", "combined"]),
  toolVersions: z.record(z.string(), ShortText),
  configurationHash: Sha256,
  exclusions: z.array(z.string().max(512)).max(100),
  readOnly: z.literal(true),
  startedAt: EpochMs,
  finishedAt: EpochMs.optional(),
});

export type VulnerabilityFinding = z.infer<typeof VulnerabilityFinding>;
export type SecretFinding = z.infer<typeof SecretFinding>;
export type ScanRun = z.infer<typeof ScanRun>;
