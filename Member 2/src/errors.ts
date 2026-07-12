export type ErrorCode =
  | "UNAUTHENTICATED" | "FORBIDDEN" | "CONFLICT" | "LOST_LEASE" | "TOO_LARGE"
  | "VALIDATION_FAILED" | "RATE_LIMITED" | "NOT_FOUND" | "POLICY_DENIED"
  | "PROVIDER_UNAVAILABLE" | "UPSTREAM_FAILED";

export class ControlPlaneError extends Error {
  constructor(
    public readonly code: ErrorCode,
    message: string,
    public readonly status: number,
    public readonly retryable = false,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ControlPlaneError";
  }

  toJSON() {
    return {
      error: { code: this.code, message: this.message, retryable: this.retryable, ...(this.details ? { details: this.details } : {}) },
    };
  }
}

export function safeErrorResponse(error: unknown): Response {
  const known = error instanceof ControlPlaneError
    ? error
    : new ControlPlaneError("UPSTREAM_FAILED", "Unexpected control-plane failure", 500, true);
  return Response.json(known.toJSON(), { status: known.status, headers: known.status === 429 ? { "Retry-After": "1" } : undefined });
}
