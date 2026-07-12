import { NextResponse } from "next/server";

const message = "GitHub credentials are managed by the Hermes GitHub App in the server-side Member 2 control plane. Browser-supplied personal access tokens are not accepted.";

export async function POST() {
  return NextResponse.json({ error: message, code: "GITHUB_APP_REQUIRED" }, { status: 410 });
}

export async function DELETE() {
  return NextResponse.json({ error: message, code: "SERVER_MANAGED_CREDENTIAL" }, { status: 405, headers: { Allow: "GET" } });
}

export async function GET() {
  return NextResponse.json({ connected: Boolean(process.env.GITHUB_APP_ID && process.env.GITHUB_APP_INSTALLATION_CONFIGURED), credentialType: "github_app", installUrl: process.env.GITHUB_APP_INSTALL_URL ?? null, browserTokenAccepted: false });
}
