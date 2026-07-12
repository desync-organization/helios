/**
 * POST /api/auth/github
 *
 * Saves a GitHub Personal Access Token (classic) to .env.local
 * so it persists across server restarts.
 *
 * DELETE /api/auth/github
 *
 * Removes the stored GitHub PAT.
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
    // Add a blank line separator if the file already has content
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
 * Save the GitHub PAT.
 */
export async function POST(request: NextRequest) {
  try {
    const { token } = (await request.json()) as { token: string };

    if (!token || typeof token !== "string" || token.trim().length === 0) {
      return NextResponse.json(
        { error: "A valid GitHub token is required." },
        { status: 400 },
      );
    }

    // Validate the token against the GitHub API
    const ghRes = await fetch("https://api.github.com/user", {
      headers: {
        Authorization: `Bearer ${token.trim()}`,
        Accept: "application/vnd.github+json",
      },
    });

    if (!ghRes.ok) {
      return NextResponse.json(
        { error: "Invalid GitHub token — could not authenticate." },
        { status: 401 },
      );
    }

    const ghUser = await ghRes.json();

    // Persist to .env.local
    let content = await readEnvFile();
    content = upsertEnvVar(content, "GITHUB_TOKEN", token.trim());
    content = upsertEnvVar(content, "GITHUB_OWNER", ghUser.login);
    await writeFile(ENV_PATH, content, "utf-8");

    return NextResponse.json({
      success: true,
      username: ghUser.login,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/**
 * Remove the stored GitHub PAT.
 */
export async function DELETE() {
  try {
    let content = await readEnvFile();
    content = removeEnvVar(content, "GITHUB_TOKEN");
    content = removeEnvVar(content, "GITHUB_OWNER");
    await writeFile(ENV_PATH, content, "utf-8");

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
