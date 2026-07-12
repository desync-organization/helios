# Deployment boundaries

Convex is the canonical store. The Worker is the only internet ingress and the only process configured
with GitHub App or provider credentials. The Helios runtime and Member 3 gateway receive only the
runtime bearer token; the browser receives none of these values.

1. Create a Convex deployment and set `CONTROL_PLANE_INGEST_TOKEN` in its server environment.
2. Deploy `infra/wrangler.toml`; add every secret listed in its final comment using `wrangler secret put`.
3. Register the GitHub App from `github-app-manifest.json`, replace placeholder URLs, and install it only
   on explicitly approved repositories.
4. Run `bun run demo:seed` with the repository/installation IDs in the local environment. Seed defaults
   to `dry-run`; move to `pr-only`, validate all three modes, and only then explicitly set `live`.
5. Point the GitHub webhook to `/webhooks/github` and verify `/status` plus `bun run demo:check`.

The App intentionally lacks administration, environments, secrets, and repository-hook mutation
permissions. Release publication and advisory publication are not implemented actions.
