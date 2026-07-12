import { z } from "zod";

const PREFIXES = {
  task: "tsk",
  run: "run",
  span: "spn",
  artifact: "art",
  event: "evt",
  finding: "fnd",
  agent: "agt",
  adapter: "adp",
  policy: "pol",
  writeback: "wba",
  evalCase: "evc",
  evalRun: "evr",
  alert: "alt",
  entity: "ent",
  scan: "scn",
  backlog: "bch",
  providerCall: "prc",
} as const;

type PrefixKey = keyof typeof PREFIXES;
type BrandedId<K extends PrefixKey> = string & { readonly __brand: K };

export function idSchema<K extends PrefixKey>(kind: K) {
  return z.string().regex(new RegExp(`^${PREFIXES[kind]}_[0-9A-HJKMNP-TV-Z]{26}$`), `invalid ${kind} ID`) as unknown as z.ZodType<BrandedId<K>>;
}

export const TaskId = idSchema("task");
export const RunId = idSchema("run");
export const SpanId = idSchema("span");
export const ArtifactId = idSchema("artifact");
export const EventId = idSchema("event");
export const FindingId = idSchema("finding");
export const AgentId = idSchema("agent");
export const AdapterId = idSchema("adapter");
export const PolicyId = idSchema("policy");
export const WritebackId = idSchema("writeback");
export const EvalCaseId = idSchema("evalCase");
export const EvalRunId = idSchema("evalRun");
export const AlertId = idSchema("alert");
export const EntityId = idSchema("entity");
export const ScanId = idSchema("scan");
export const BacklogBatchId = idSchema("backlog");
export const ProviderCallId = idSchema("providerCall");

const ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
export function newId<K extends PrefixKey>(kind: K, now = Date.now()): BrandedId<K> {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let value = BigInt(now);
  for (const byte of bytes) value = (value << 8n) | BigInt(byte);
  let encoded = "";
  for (let index = 0; index < 26; index += 1) {
    encoded = ENCODING[Number(value & 31n)] + encoded;
    value >>= 5n;
  }
  return `${PREFIXES[kind]}_${encoded}` as BrandedId<K>;
}

export type TaskId = z.infer<typeof TaskId>;
export type RunId = z.infer<typeof RunId>;
export type SpanId = z.infer<typeof SpanId>;
export type ArtifactId = z.infer<typeof ArtifactId>;
export type EventId = z.infer<typeof EventId>;
export type FindingId = z.infer<typeof FindingId>;
export type AgentId = z.infer<typeof AgentId>;
export type AdapterId = z.infer<typeof AdapterId>;
export type WritebackId = z.infer<typeof WritebackId>;
