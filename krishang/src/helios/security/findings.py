import hashlib

from helios.contracts.security import Finding


def finding_fingerprint(kind: str, rule_id: str, path: str, evidence: str) -> str:
    stable = f"{kind}\0{rule_id}\0{path}\0{evidence.strip().lower()}"
    return hashlib.sha256(stable.encode()).hexdigest()


def make_finding(**values) -> Finding:
    values.setdefault("fingerprint", finding_fingerprint(values["kind"], values["rule_id"], values["path"], values.get("evidence", "")))
    return Finding(**values)

