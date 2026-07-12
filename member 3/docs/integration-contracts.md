# Member 3 Integration Contracts

Member 1 supplies versioned eval results, canonical events, exact model/adapter identity, loader smoke,
rollback evidence, and fixture/live execution hooks. Member 2 supplies canonical cursor replay,
task-draft creation with idempotency, wrapper status, persisted terminal result URLs, eval/report
persistence, and atomic adapter activation.

Proposed gateway endpoints are `POST /gateway/task-drafts`, `GET /gateway/events?after=...`, and
`GET /gateway/status`. Freeze their JSON fixtures with both consumers before integration. The gateway
never receives GitHub/provider credentials, maintains task truth, or turns a client prompt into live
permission. Contract changes require exact JSON, version impact, and coordinated tests before merge.
