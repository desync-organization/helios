from helios.contracts.security import Finding


def remediation_plan(findings: list[Finding], permitted: bool) -> dict:
    if not permitted:
        return {"authorized": False, "actions": [], "reason": "audit is read-only"}
    return {
        "authorized": True,
        "actions": [
            {"fingerprint": finding.fingerprint, "change": finding.remediation, "tests": ["targeted regression", "relevant scanner rescan"]}
            for finding in findings if finding.remediation
        ],
        "publication": "human-controlled",
    }

