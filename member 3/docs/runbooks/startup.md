# Local Startup and Integration

1. Install core tooling with `python -m pip install -e ".[dev]"` from `member 3/`.
2. Start Member 2's canonical control plane and verify its `/gateway/*` contract.
3. Set `HERMES_CONTROL_PLANE_URL`, the server-to-server upstream token, and a short-lived local client
   ticket in `HERMES_GATEWAY_CLIENT_TOKEN`; never use a GitHub/provider credential.
4. Run `python -m hermes_gateway`, then check `http://127.0.0.1:9100/health` and `/status`.
5. Configure the frozen client URL to `ws://127.0.0.1:9100/ws?ticket=<short-lived-ticket>` and run the
   root frontend with `bun dev`.

If the control plane is absent, health is `degraded` and prompt creation fails safely.

