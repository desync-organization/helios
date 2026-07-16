from helios.contracts.security import Finding


def normalize_findings(findings: list[Finding]) -> list[Finding]:
    by_fingerprint: dict[str, Finding] = {}
    for finding in findings:
        existing = by_fingerprint.get(finding.fingerprint)
        if not existing or finding.confidence == "high":
            by_fingerprint[finding.fingerprint] = finding
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "warning": 2, "low": 3, "info": 4}
    return sorted(
        by_fingerprint.values(),
        key=lambda item: (severity_rank.get(item.severity.lower(), 5), item.path, item.rule_id),
    )
