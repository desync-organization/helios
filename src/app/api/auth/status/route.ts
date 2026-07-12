import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    githubConnected: Boolean(process.env.GITHUB_APP_ID && process.env.GITHUB_APP_INSTALLATION_CONFIGURED),
    githubCredentialType: "github_app",
    githubInstallUrl: process.env.GITHUB_APP_INSTALL_URL ?? null,
    vercelConnected: Boolean(process.env.VERCEL_INTEGRATION_CONFIGURED),
    vercelCredentialType: "server_managed",
    browserTokenStorageEnabled: false,
  });
}
