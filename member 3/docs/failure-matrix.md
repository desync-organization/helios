# Reliability Failure Matrix

This matrix separates Member 3-owned deterministic coverage from merged-system acceptance. A checked
unit row means the local failure behavior is tested, not that the external dependency has been proven.

| Failure | Local coverage | Merged proof required |
|---|---|---|
| Invalid/oversized/rate-abusive prompt | `gateway/tests/test_gateway.py` | Browser reconnect rehearsal |
| Duplicate prompt | Gateway idempotency test | Member 2 idempotency audit row |
| Secret/private field projection | Recursive redaction test | Browser bundle/response scan |
| Missing completion URL | Canonical event validation | Real GitHub result URL |
| Out-of-order/duplicate event | Hub reliability test | Cursor feed disconnect/replay |
| Control-plane outage | Degraded health/task error | Convex outage and outbox replay |
| Adapter mismatch/regression | Preflight/promotion gates | Member 1 loader and rollback |
| Failed build/test/security check | Gauntlet automatic failure | Member 1 execution evidence |
| Unauthorized scan/public disclosure | Security fixtures/gates | Member 2 policy audit |
| Provider/rate-limit/base-SHA failure | Not locally owned | Worker/GitHub integration run |
| Global pause/lost lease | Not locally owned | Member 1/2 concurrent acceptance |

Do not mark a merged-proof column complete until the evidence index contains exact IDs, versions,
timestamps, and real URLs where applicable.

