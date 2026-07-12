export function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

export function serverToken(name: string): string {
  const value = required(name);
  if (value.length < 32 || value.startsWith("replace-with")) throw new Error(`${name} must be a non-placeholder value of at least 32 characters`);
  return value;
}

export async function controlPost(path: string, payload: unknown): Promise<unknown> {
  const base = required("CONTROL_PLANE_URL").replace(/\/$/, "");
  const response = await fetch(`${base}${path}`, { method: "POST", headers: { Authorization: `Bearer ${serverToken("CONTROL_PLANE_INGEST_TOKEN")}`, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error(`${path} returned ${response.status}: ${(await response.text()).slice(0, 500)}`);
  return response.json();
}
