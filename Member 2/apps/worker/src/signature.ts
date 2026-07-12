function hex(bytes: ArrayBuffer): string {
  return Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function constantTimeHexEqual(left: string, right: string): boolean {
  const length = Math.max(left.length, right.length, 1);
  let difference = left.length ^ right.length;
  for (let index = 0; index < length; index += 1) difference |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  return difference === 0;
}

export async function verifyGitHubSignature(rawBody: ArrayBuffer, signatureHeader: string | null, secret: string): Promise<boolean> {
  if (!signatureHeader?.startsWith("sha256=") || !secret) return false;
  const signature = signatureHeader.slice(7).toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(signature)) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const expected = hex(await crypto.subtle.sign("HMAC", key, rawBody));
  return constantTimeHexEqual(signature, expected);
}
