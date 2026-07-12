# Maintainer, Builder, and Security Mode Usage

All prompts enter through the authenticated gateway as permission-free task drafts. Member 2 policy
confirms repository, mode, allowed actions, data classification, egress, and expiry before Member 1
execution.

- `maintain`: expect a classification/reply or tested PR intent; completion requires a persisted GitHub
  URL and fast tasks target under 60 seconds warmed.
- `build`: require bounded requirements, non-goals, architecture, implementation DAG, complete files,
  build/tests/security evidence, critic verdict, and PR/build manifest. Escalate material auth,
  payment, privacy, deployment, or data-shape decisions.
- `security_audit`: require allowlist and opt-in; default to read-only local scans and a private redacted
  report. Remediation is a separate permissioned task with tests and rescan.

Never treat a local patch, dry run, fixture, generated response, or queue receipt as completion.

