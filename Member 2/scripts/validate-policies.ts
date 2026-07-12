import { parse } from "yaml";
import { z } from "zod";

const Rule = z.object({ id: z.string().regex(/^[a-z][a-z0-9_.-]{2,127}$/), description: z.string().min(1), severity: z.enum(["info", "warning", "blocking", "critical"]), version: z.string().regex(/^\d+\.\d+\.\d+$/), enabled: z.boolean(), parameters: z.record(z.string(), z.unknown()) }).strict();
const File = z.object({ schemaVersion: z.literal(1), name: z.string().min(1), version: z.string().regex(/^\d+\.\d+\.\d+$/), rules: z.array(Rule).min(1) }).strict();
const names = ["triage", "autonomy", "escalation", "voice", "build", "security", "data-egress", "retention"];
const ids = new Set<string>();
for (const name of names) {
  const parsed = File.parse(parse(await Bun.file(new URL(`../policy/${name}.yaml`, import.meta.url)).text()));
  for (const rule of parsed.rules) {
    if (ids.has(rule.id)) throw new Error(`Duplicate policy rule ID: ${rule.id}`);
    ids.add(rule.id);
  }
}
console.log(`Validated ${names.length} policy bundles and ${ids.size} stable rules.`);
