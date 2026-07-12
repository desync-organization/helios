/**
 * GET /api/auth/status
 *
 * Returns the current authentication status by checking whether
 * tokens exist in the environment / .env.local file.
 */
import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

async function readEnvLocal(): Promise<Record<string, string>> {
  try {
    // Stored in /secrets at project root (temporary — will be refactored)
    const envPath = join(process.cwd(), "..", "secrets", ".env.local");
    const content = await readFile(envPath, "utf-8");
    const vars: Record<string, string> = {};
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eqIdx = trimmed.indexOf("=");
      if (eqIdx === -1) continue;
      const key = trimmed.slice(0, eqIdx).trim();
      const value = trimmed.slice(eqIdx + 1).trim();
      vars[key] = value;
    }
    return vars;
  } catch {
    return {};
  }
}

export async function GET() {
  const env = await readEnvLocal();

  const vercelToken = env.VERCEL_TOKEN || process.env.VERCEL_TOKEN || "";
  const githubToken = env.GITHUB_TOKEN || process.env.GITHUB_TOKEN || "";

  let vercelUser = null;

  // If we have a Vercel token, fetch user info
  if (vercelToken) {
    try {
      const res = await fetch("https://api.vercel.com/v2/user", {
        headers: { Authorization: `Bearer ${vercelToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        vercelUser = {
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          username: data.user.username,
        };
      }
    } catch {
      /* token may be expired */
    }
  }

  return NextResponse.json({
    vercelConnected: !!vercelToken && !!vercelUser,
    vercelUser,
    githubConnected: !!githubToken,
  });
}
