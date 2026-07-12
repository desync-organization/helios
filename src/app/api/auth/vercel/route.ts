/**
 * POST /api/auth/vercel
 *
 * Saves a Vercel Personal Access Token to .env.local
 * and validates it against the Vercel API.
 *
 * DELETE /api/auth/vercel
 *
 * Removes the stored Vercel token.
 */
import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile } from "fs/promises";
import { join } from "path";

// Stored in /secrets at project root (temporary — will be refactored)
const ENV_PATH = join(process.cwd(), "..", "secrets", ".env.local");

async function readEnvFile(): Promise<string> {
  try {
    return await readFile(ENV_PATH, "utf-8");
  } catch {
    return "";
  }
}

function upsertEnvVar(content: string, key: string, value: string): string {
  const lines = content.split("\n");
  const idx = lines.findIndex((l) => l.trim().startsWith(`${key}=`));
  const entry = `${key}=${value}`;

  if (idx !== -1) {
    lines[idx] = entry;
  } else {
    if (lines.length > 0 && lines[lines.length - 1].trim() !== "") {
      lines.push("");
    }
    lines.push(entry);
  }

  return lines.join("\n");
}

function removeEnvVar(content: string, key: string): string {
  return content
    .split("\n")
    .filter((l) => !l.trim().startsWith(`${key}=`))
    .join("\n");
}

/**
 * Save the Vercel PAT.
 */
export async function POST(request: NextRequest) {
  try {
    const { token } = (await request.json()) as { token: string };

    if (!token || typeof token !== "string" || token.trim().length === 0) {
      return NextResponse.json(
        { error: "A valid Vercel token is required." },
        { status: 400 },
      );
    }

    // Validate the token against the Vercel API
    const vercelRes = await fetch("https://api.vercel.com/v2/user", {
      headers: { Authorization: `Bearer ${token.trim()}` },
    });

    if (!vercelRes.ok) {
      return NextResponse.json(
        { error: "Invalid Vercel token — could not authenticate." },
        { status: 401 },
      );
    }

    const data = await vercelRes.json();

    // Persist to .env.local
    let content = await readEnvFile();
    content = upsertEnvVar(content, "VERCEL_TOKEN", token.trim());
    await writeFile(ENV_PATH, content, "utf-8");

    return NextResponse.json({
      success: true,
      user: {
        id: data.user.id,
        email: data.user.email,
        name: data.user.name,
        username: data.user.username,
      },
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/**
 * Remove the stored Vercel token.
 */
export async function DELETE() {
  try {
    let content = await readEnvFile();
    content = removeEnvVar(content, "VERCEL_TOKEN");
    await writeFile(ENV_PATH, content, "utf-8");

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
