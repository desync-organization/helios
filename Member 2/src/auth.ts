import { ControlPlaneError } from "./errors";

function toBytes(value: string): Uint8Array {
  return new TextEncoder().encode(value);
}

export async function constantTimeEqual(left: string, right: string): Promise<boolean> {
  const a = toBytes(left);
  const b = toBytes(right);
  const length = Math.max(a.length, b.length, 1);
  const paddedA = new Uint8Array(length);
  const paddedB = new Uint8Array(length);
  paddedA.set(a.subarray(0, length));
  paddedB.set(b.subarray(0, length));
  let difference = a.length ^ b.length;
  for (let index = 0; index < length; index += 1) difference |= paddedA[index] ^ paddedB[index];
  return difference === 0;
}

export async function requireBearer(request: Request, expectedToken: string): Promise<void> {
  if (!expectedToken || expectedToken.length < 32) throw new ControlPlaneError("FORBIDDEN", "Server authentication is not configured", 503, false);
  const header = request.headers.get("Authorization") ?? "";
  const supplied = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!(await constantTimeEqual(supplied, expectedToken))) throw new ControlPlaneError("UNAUTHENTICATED", "Invalid bearer token", 401, false);
}

export async function readBoundedJson<T>(request: Request, maximumBytes = 131_072): Promise<T> {
  const declared = Number(request.headers.get("Content-Length") ?? "0");
  if (declared > maximumBytes) throw new ControlPlaneError("TOO_LARGE", "Request body exceeds the configured limit", 413, false);
  const body = await request.arrayBuffer();
  if (body.byteLength > maximumBytes) throw new ControlPlaneError("TOO_LARGE", "Request body exceeds the configured limit", 413, false);
  try {
    return JSON.parse(new TextDecoder().decode(body)) as T;
  } catch {
    throw new ControlPlaneError("VALIDATION_FAILED", "Request body must be valid JSON", 422, false);
  }
}
