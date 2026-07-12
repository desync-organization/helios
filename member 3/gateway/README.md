# Realtime Compatibility Gateway

The gateway listens on `127.0.0.1:9100` and projects Member 2's canonical cursor feed into the direct
messages consumed by the frozen Next.js client. It does not persist task/run truth or hold GitHub and
provider credentials.

```powershell
$env:HERMES_CONTROL_PLANE_URL = "http://127.0.0.1:3210"
$env:HERMES_GATEWAY_UPSTREAM_TOKEN = "server-to-server-session-token"
$env:HERMES_GATEWAY_CLIENT_TOKEN = "short-lived-local-client-token"
python -m hermes_gateway
```

Use `ws://localhost:9100/ws?token=...` for task creation. An explicitly enabled unauthenticated demo
connection (`HERMES_ALLOW_READONLY_DEMO=true`) is read-only and receives redacted events only. `/status`
exposes wrapper status but reports that the frozen client does not consume it. The proposed Member 2
adapter endpoints are `POST /gateway/task-drafts`, `GET /gateway/events?after=...`, and
`GET /gateway/status`; coordinate these contracts before integration.

