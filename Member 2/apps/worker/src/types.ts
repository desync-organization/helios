export interface WorkerEnv {
  GITHUB_WEBHOOK_SECRET: string;
  CONTROL_PLANE_URL: string;
  CONTROL_PLANE_INGEST_TOKEN: string;
  RUNTIME_BEARER_TOKEN: string;
  PROVIDER_PROXY_TOKEN: string;
  HERMES_BOT_LOGIN: string;
  GITHUB_APP_ID: string;
  GITHUB_APP_PRIVATE_KEY: string;
  WORKERS_AI_ENDPOINT?: string;
  WORKERS_AI_TOKEN?: string;
  HAIKU_ENDPOINT?: string;
  HAIKU_API_KEY?: string;
  LINKUP_ENDPOINT?: string;
  LINKUP_API_KEY?: string;
  ELEVENLABS_ENDPOINT?: string;
  ELEVENLABS_API_KEY?: string;
  ENVIRONMENT: "development" | "staging" | "production";
}

export interface ExecutionContextLike { waitUntil(promise: Promise<unknown>): void }

export interface GitHubEnvelope {
  event: string;
  deliveryId: string;
  hookId?: string;
  payload: Record<string, unknown>;
}
