const SECRET_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: "github_token", pattern: /\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b/g },
  { name: "aws_access_key", pattern: /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/g },
  { name: "private_key", pattern: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g },
  { name: "bearer_token", pattern: /\bBearer\s+[A-Za-z0-9._~+\/-]{16,}=*\b/gi },
  { name: "credential_assignment", pattern: /\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*["']?[A-Za-z0-9._~+\/-]{12,}["']?/gi },
  { name: "jwt", pattern: /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g },
];

const PII_PATTERNS = [
  { name: "email", pattern: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi },
  { name: "ipv4", pattern: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g },
];

export interface RedactionResult {
  value: string;
  findings: Array<{ type: string; fingerprint: string }>;
}

async function fingerprint(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function redactSensitive(input: string, includePii = true): Promise<RedactionResult> {
  let value = input;
  const findings: RedactionResult["findings"] = [];
  for (const detector of includePii ? [...SECRET_PATTERNS, ...PII_PATTERNS] : SECRET_PATTERNS) {
    const matches = [...value.matchAll(new RegExp(detector.pattern.source, detector.pattern.flags))];
    for (const match of matches) findings.push({ type: detector.name, fingerprint: await fingerprint(match[0]) });
    value = value.replace(new RegExp(detector.pattern.source, detector.pattern.flags), `[REDACTED:${detector.name}]`);
  }
  return { value, findings };
}

export function containsSuspectedSecret(input: string): boolean {
  return SECRET_PATTERNS.some(({ pattern }) => new RegExp(pattern.source, pattern.flags).test(input));
}

export function assertNoRawSecrets(value: unknown): void {
  const serialized = typeof value === "string" ? value : JSON.stringify(value);
  if (containsSuspectedSecret(serialized)) throw new Error("Raw secret-like content is forbidden at this boundary");
}
