import { NextResponse } from "next/server";

const message = "Provider credentials are server-managed. Browser-supplied Vercel personal access tokens are disabled by the Hermes credential boundary.";

export async function POST() {
  return NextResponse.json({ error: message, code: "SERVER_MANAGED_CREDENTIAL" }, { status: 410 });
}

export async function DELETE() {
  return NextResponse.json({ error: message, code: "SERVER_MANAGED_CREDENTIAL" }, { status: 405, headers: { Allow: "GET" } });
}

export async function GET() {
  return NextResponse.json({ connected: Boolean(process.env.VERCEL_INTEGRATION_CONFIGURED), credentialType: "server_managed", browserTokenAccepted: false });
}
