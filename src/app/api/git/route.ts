import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { NextRequest, NextResponse } from "next/server";

const execFileAsync = promisify(execFile);
const READ_ONLY_COMMANDS: Record<string, string[]> = {
  "git branch": ["branch", "--list"],
  "git branch -a": ["branch", "--all", "--list"],
};

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json() as { command?: unknown };
    if (typeof body.command !== "string") return NextResponse.json({ error: "Command is required" }, { status: 400 });
    const args = READ_ONLY_COMMANDS[body.command];
    if (!args) return NextResponse.json({ error: "Only read-only branch listing is allowed. Branch creation, checkout, merge, and deletion must go through the policy-gated control plane." }, { status: 403 });
    const { stdout, stderr } = await execFileAsync("git", args, { cwd: process.cwd(), timeout: 5_000, maxBuffer: 256 * 1024, env: { PATH: process.env.PATH ?? "/usr/bin:/bin", HOME: process.env.HOME ?? "/tmp", LANG: "C", NODE_ENV: process.env.NODE_ENV ?? "production" } });
    return NextResponse.json({ output: stdout || stderr });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Failed to list branches" }, { status: 500 });
  }
}
