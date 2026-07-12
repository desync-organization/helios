import { z } from "zod";

export const SCHEMA_VERSION = 1 as const;
export const SchemaVersion = z.literal(SCHEMA_VERSION);
export const EpochMs = z.number().int().nonnegative().max(8_640_000_000_000_000);
export const ShortText = z.string().trim().min(1).max(256);
export const MediumText = z.string().max(4_096);
export const BodyText = z.string().max(128_000);
export const Sha256 = z.string().regex(/^[a-f0-9]{64}$/i, "expected a SHA-256 hex digest");
export const GitSha = z.string().regex(/^[a-f0-9]{40}$/i, "expected a Git SHA-1 hex digest");
export const HttpsUrl = z.string().url().max(2_048).refine((value) => value.startsWith("https://"), "HTTPS URL required");
export const DataClassification = z.enum(["public", "internal", "private", "restricted"]);
export const RetentionClass = z.enum(["ephemeral", "short", "standard", "audit", "restricted"]);
export const ErrorRecord = z.object({
  code: z.string().min(1).max(64),
  message: z.string().min(1).max(2_048),
  retryable: z.boolean(),
  details: z.record(z.string(), z.unknown()).optional(),
}).strict();

export type ErrorRecord = z.infer<typeof ErrorRecord>;
export type DataClassification = z.infer<typeof DataClassification>;

export function externalObject<T extends z.ZodRawShape>(shape: T) {
  return z.object({ schemaVersion: SchemaVersion, ...shape }).strict();
}
