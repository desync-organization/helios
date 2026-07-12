# Security Audit and Consent

Confirm repository identity, allowlist, `securityAuditOptIn`, read-only scope, scanners, network policy,
retention, and remediation permission before an audit. External/destructive scanning, exploitation,
secret access, and public disclosure are prohibited. Redact secret values immediately; retain only
fingerprints, type, and location. Report severity, confidence, reachability, and exploitability
separately with authoritative advisory timestamps.

Remediation requires separate approval, minimal changes, tests, rescan, before/after findings, and a
private PR intent. A read-only run must perform zero mutation.
