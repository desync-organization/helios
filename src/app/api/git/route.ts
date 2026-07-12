/**
 * API route for executing git commands.
 * This enables the multiverse view to manage git branches.
 * 
 * NOTE: This route only works in development mode with Node.js runtime.
 * For Tauri production builds, git commands should be executed via Tauri commands
 * in the Rust backend instead.
 */
import { exec } from "child_process";
import { promisify } from "util";
import { NextRequest, NextResponse } from "next/server";

const execAsync = promisify(exec);

interface GitCommandRequest {
  command: string;
}

interface GitCommandResponse {
  output: string;
  error?: string;
}

/**
 * Whitelist of allowed git commands for security.
 */
const ALLOWED_COMMANDS = [
  /^git branch$/,
  /^git branch -a$/,
  /^git branch [a-zA-Z0-9_/-]+$/,
  /^git branch -d [a-zA-Z0-9_/-]+$/,
  /^git branch -D [a-zA-Z0-9_/-]+$/,
  /^git checkout [a-zA-Z0-9_/-]+$/,
  /^git merge [a-zA-Z0-9_/-]+$/,
];

/**
 * Validate that the command is safe to execute.
 */
function isCommandAllowed(command: string): boolean {
  return ALLOWED_COMMANDS.some((pattern) => pattern.test(command));
}

/**
 * POST /api/git
 * Execute a git command and return the output.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body = (await request.json()) as GitCommandRequest;
    const { command } = body;

    if (!command) {
      return NextResponse.json(
        { error: "Command is required" },
        { status: 400 },
      );
    }

    // Security: Only allow whitelisted commands
    if (!isCommandAllowed(command)) {
      return NextResponse.json(
        { error: "Command not allowed" },
        { status: 403 },
      );
    }

    // Execute the git command
    const { stdout, stderr } = await execAsync(command, {
      cwd: process.cwd(),
      maxBuffer: 1024 * 1024, // 1MB buffer
    });

    const response: GitCommandResponse = {
      output: stdout || stderr,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Git command execution error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to execute command",
      },
      { status: 500 },
    );
  }
}
