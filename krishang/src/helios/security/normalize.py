from helios.contracts.security import Finding


def normalize_findings(findings: list[Finding]) -> list[Finding]:
    by_fingerprint: dict[str, Finding] = {}
    for finding in findings:
        existing = by_fingerprint.get(finding.fingerprint)
        if not existing or finding.confidence == "high":
            by_fingerprint[finding.fingerprint] = finding
    return sorted(by_fingerprint.values(), key=lambda item: (item.severity, item.path, item.rule_id))

