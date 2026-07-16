import { create } from "zustand";

/* ------------------------------------------------------------------ */
/*  Public types                                                       */
/* ------------------------------------------------------------------ */

/** Status values matching the backend WrapperStatus type. */
export type WrapperStatus = "IDLE" | "THINKING" | "WORKING" | "BLOCKED";

/** Serialised wrapper record coming from the orchestrator. */
export interface WrapperInfo {
  id: string;
  type: string;
  status: WrapperStatus;
  lastSeen: number;
  meta: {
    name: string;
    type: string;
    drones?: number;
    [key: string]: unknown;
  };
}

/** A single message in the chat timeline. */
export interface ChatMessage {
  id: string;
  author: string;
  avatar: string;
  content: string;
  timestamp: Date;
  isUser: boolean;
}

/** A generated code artifact from a specialist wrapper. */
export interface CodeArtifact {
  id: string;
  filename: string;
  language: string;
  code: string;
  type: string;
  wrapper: string;
  agent: string;
  timestamp: Date;
  status: "streaming" | "complete";
  progress: number;
  componentName?: string;
}

/** A single LLM call token usage record. */
export interface TokenUsageEntry {
  office: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_s: number;
  timestamp: number;
}

/** Per-office aggregated stats. */
export interface PerOfficeStat {
  office: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  totalLatency: number;
}

/** Aggregated cost summary derived from tokenUsageLog. */
export interface CostSummary {
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCostUsd: number;
  totalCalls: number;
  perOffice: PerOfficeStat[];
}

/* ------------------------------------------------------------------ */
/*  Envelope – mirrors backend/orchestrator/src/types.ts               */
/* ------------------------------------------------------------------ */

interface Envelope<TPayload = unknown> {
  type: string;
  id?: string;
  src?: string;
  dst?: string;
  ts?: number;
  payload?: TPayload;
}

interface DirectMessage {
  type: string;
  data?: unknown;
  artifact?: unknown;
  id?: unknown;
  filename?: unknown;
  language?: unknown;
  code?: unknown;
  artifactType?: unknown;
  progress?: unknown;
  files?: unknown;
  githubUrl?: unknown;
  projectName?: unknown;
}

/* ------------------------------------------------------------------ */
/*  Store interface                                                    */
/* ------------------------------------------------------------------ */

interface OrchestratorState {
  wrappers: Record<string, WrapperInfo>;
  connected: boolean;
  chatMessages: ChatMessage[];
  agentMessages: ChatMessage[];
  terminalLogs: string[];
  artifacts: CodeArtifact[];
  projectFiles: string[];
  activeArtifactId: string | null;
  projectGithubUrl: string | null;
  projectName: string | null;
  projectRepoName: string | null;
  tokenUsageLog: TokenUsageEntry[];
  costSummary: CostSummary;
  costMessages: string[];

  connect: (orchestratorUrl: string) => void;
  disconnect: () => void;
  sendChatMessage: (text: string) => void;
  sendEnvelope: (envelope: Envelope) => void;
  setActiveArtifact: (id: string) => void;
  clearArtifacts: () => void;
  clearTerminal: () => void;
  clearCostData: () => void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonEmptyString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function inferArtifactLanguage(filename: string): string {
  const extension = filename.split(".").pop()?.toLowerCase();
  const languages: Record<string, string> = {
    css: "css",
    html: "html",
    js: "javascript",
    jsx: "javascript",
    json: "json",
    ts: "typescript",
    tsx: "typescript",
  };
  return (extension && languages[extension]) || "text";
}

function inferArtifactType(filename: string, language: string): string {
  const basename = filename.replace(/\\/g, "/").split("/").pop()?.toLowerCase();
  if (basename === "index.html" || language === "html") return "html";
  if (basename === "styles.css" || language === "css") return "style";
  if (basename === "app.js" || language === "javascript") return "script";
  return "file";
}

function artifactPayload(message: DirectMessage): Record<string, unknown> {
  if (isRecord(message.data)) return message.data;
  if (isRecord(message.artifact)) return message.artifact;
  return message as unknown as Record<string, unknown>;
}

function upsertArtifactState(
  state: OrchestratorState,
  payload: Record<string, unknown>,
  defaultAgent: string,
): Partial<OrchestratorState> {
  const incomingFilename = nonEmptyString(payload.filename);
  const incomingId = nonEmptyString(payload.id);
  const artifactId = incomingId ?? (incomingFilename
    ? `artifact:${incomingFilename}`
    : `artifact:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`);
  const existingIndex = state.artifacts.findIndex((artifact) => artifact.id === artifactId);
  const existing = existingIndex >= 0 ? state.artifacts[existingIndex] : undefined;
  const filename = incomingFilename ?? existing?.filename ?? "untitled";
  const language = nonEmptyString(payload.language) ?? existing?.language ?? inferArtifactLanguage(filename);
  const incomingType = nonEmptyString(payload.artifactType)
    ?? nonEmptyString(payload.artifact_type)
    ?? nonEmptyString(payload.type);
  const artifactType = incomingType && incomingType !== "artifact"
    ? incomingType
    : existing?.type ?? inferArtifactType(filename, language);
  const rawProgress = typeof payload.progress === "number"
    ? payload.progress
    : Number(payload.progress ?? 100);
  const progress = Number.isFinite(rawProgress)
    ? Math.min(100, Math.max(0, rawProgress))
    : 100;
  const agent = nonEmptyString(payload.agent) ?? nonEmptyString(payload.wrapper) ?? defaultAgent;
  const artifact: CodeArtifact = {
    id: artifactId,
    filename,
    language,
    code: typeof payload.code === "string" ? payload.code : existing?.code ?? "",
    type: artifactType,
    wrapper: agent,
    agent,
    timestamp: existing?.timestamp ?? new Date(),
    status: progress >= 100 ? "complete" : "streaming",
    progress,
    componentName: nonEmptyString(payload.componentName) ?? existing?.componentName,
  };
  const artifacts = [...state.artifacts];

  if (existingIndex >= 0) {
    artifacts[existingIndex] = artifact;
  } else {
    artifacts.push(artifact);
  }

  const currentProjectFiles = existing?.filename && existing.filename !== filename
    ? state.projectFiles.filter((projectFile) => projectFile !== existing.filename)
    : state.projectFiles;

  return {
    artifacts,
    projectFiles: currentProjectFiles.includes(filename)
      ? currentProjectFiles
      : [...currentProjectFiles, filename],
    activeArtifactId: state.activeArtifactId ?? artifactId,
  };
}

/* ------------------------------------------------------------------ */
/*  Singleton WebSocket bookkeeping (outside Zustand to avoid cycles)  */
/* ------------------------------------------------------------------ */

let _ws: WebSocket | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _shouldReconnect = false;
const MAX_PENDING_PROMPTS = 20;
const _pendingPrompts: string[] = [];

function clearReconnectTimer() {
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
}

function sendPrompt(websocket: WebSocket, text: string): boolean {
  if (websocket.readyState !== WebSocket.OPEN) return false;
  try {
    websocket.send(JSON.stringify({ type: "prompt", data: text }));
    return true;
  } catch {
    return false;
  }
}

function flushPendingPrompts(websocket: WebSocket) {
  while (_ws === websocket && _pendingPrompts.length > 0) {
    const prompt = _pendingPrompts[0];
    if (!sendPrompt(websocket, prompt)) return;
    _pendingPrompts.shift();
  }
}

function officeKey(office: string): string {
  return office
    .replace(/[(\[].*[)\]]/g, "")
    .replace(/-retry/g, "")
    .trim()
    .split(" ")[0] || office;
}

/** Add one usage record without rescanning the complete call history. */
export function appendCostSummary(
  summary: CostSummary,
  entry: TokenUsageEntry,
): CostSummary {
  const key = officeKey(entry.office);
  const existingIndex = summary.perOffice.findIndex((item) => item.office === key);
  const perOffice = [...summary.perOffice];
  const existing = existingIndex >= 0
    ? perOffice[existingIndex]
    : {
        office: key,
        calls: 0,
        inputTokens: 0,
        outputTokens: 0,
        costUsd: 0,
        totalLatency: 0,
      };
  const updated: PerOfficeStat = {
    ...existing,
    calls: existing.calls + 1,
    inputTokens: existing.inputTokens + entry.input_tokens,
    outputTokens: existing.outputTokens + entry.output_tokens,
    costUsd: existing.costUsd + entry.cost_usd,
    totalLatency: existing.totalLatency + entry.latency_s,
  };

  if (existingIndex >= 0) {
    perOffice[existingIndex] = updated;
  } else {
    perOffice.push(updated);
  }
  perOffice.sort((a, b) => b.costUsd - a.costUsd);

  return {
    totalInputTokens: summary.totalInputTokens + entry.input_tokens,
    totalOutputTokens: summary.totalOutputTokens + entry.output_tokens,
    totalCostUsd: Math.round((summary.totalCostUsd + entry.cost_usd) * 1e6) / 1e6,
    totalCalls: summary.totalCalls + 1,
    perOffice,
  };
}

/* ------------------------------------------------------------------ */
/*  Store implementation                                               */
/* ------------------------------------------------------------------ */

export const useOrchestratorStore = create<OrchestratorState>((set, get) => ({
  wrappers: {},
  connected: false,
  chatMessages: [],
  agentMessages: [],
  terminalLogs: [],
  artifacts: [],
  projectFiles: [],
  activeArtifactId: null,
  projectGithubUrl: null,
  projectName: null,
  projectRepoName: null,
  tokenUsageLog: [],
  costSummary: {
    totalInputTokens: 0,
    totalOutputTokens: 0,
    totalCostUsd: 0,
    totalCalls: 0,
    perOffice: [],
  },
  costMessages: [],

  /* ---- simple setters ---- */

  setActiveArtifact(id: string) {
    set({ activeArtifactId: id });
  },

  clearArtifacts() {
    set({
      artifacts: [],
      activeArtifactId: null,
      projectGithubUrl: null,
      projectName: null,
      projectRepoName: null,
      projectFiles: [],
    });
  },

  clearTerminal() {
    set({ terminalLogs: [] });
  },

  clearCostData() {
    set({
      tokenUsageLog: [],
      costSummary: {
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalCostUsd: 0,
        totalCalls: 0,
        perOffice: [],
      },
      costMessages: [],
    });
  },

  /* ---- send a raw envelope ---- */

  sendEnvelope(envelope: Envelope) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify(envelope));
    }
  },

  /* ---- send a user chat message (to PM via orchestrator) ---- */

  sendChatMessage(text: string) {
    // A prompt starts a fresh generated project while preserving conversation history.
    set((state) => ({
      artifacts: [],
      projectFiles: [],
      activeArtifactId: null,
      projectGithubUrl: null,
      projectName: null,
      projectRepoName: null,
      chatMessages: [
        ...state.chatMessages,
        {
          id: `msg-${Date.now()}`,
          author: "You",
          avatar: "YO",
          content: text,
          timestamp: new Date(),
          isUser: true,
        },
      ],
    }));

    // Send immediately when possible; otherwise retain the prompt until the
    // current connection reaches OPEN. A successfully sent prompt is removed
    // from the queue before any later reconnect can flush it again.
    if (!_ws || !sendPrompt(_ws, text)) {
      if (_pendingPrompts.length >= MAX_PENDING_PROMPTS) {
        _pendingPrompts.shift();
      }
      _pendingPrompts.push(text);
    }
  },

  /* ---- connect to the orchestrator WebSocket ---- */

  connect(url: string) {
    // Prevent duplicate connections
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    _shouldReconnect = true;
    clearReconnectTimer();

    try {
      const ws = new WebSocket(url);
      _ws = ws;

      ws.addEventListener("open", () => {
        if (_ws !== ws) return;
        console.log("[ml-service] connected to", url);
        set({ connected: true });
        flushPendingPrompts(ws);
      });

      ws.addEventListener("message", (event) => {
        if (_ws !== ws) return;
        let msg: DirectMessage;
        try {
          const parsed = JSON.parse(String(event.data)) as unknown;
          if (!isRecord(parsed) || typeof parsed.type !== "string") {
            throw new TypeError("message must be an object with a string type");
          }
          msg = parsed as unknown as DirectMessage;
        } catch {
          console.warn("[ml-service] invalid message", event.data);
          return;
        }

        // Handle progress updates
        if (msg.type === "progress") {
          const terminalLine = typeof msg.data === "string" ? msg.data : JSON.stringify(msg.data ?? "");
          let logLine = terminalLine;

          // Only show "ML Pipeline" as author for the starting message
          // Otherwise extract office name from content (e.g., "🏢 CEO OFFICE" -> "CEO OFFICE")
          let author = "ML Pipeline";
          let avatar = "ML";

          if (!logLine.includes("Starting ML pipeline for:")) {
            // Try to extract office name from patterns like "🏢 CEO OFFICE — ..." or "⚡️ DEVOPS OFFICE — ..."
            // Match at start of line OR after whitespace, with optional emoji prefix
            const officeMatch = logLine.match(/^(?:[🏢⚡️✅⏳🔧🚀📁🔗📤📝❌⚠️])?\s*([A-Z][A-Z\s]*(?:OFFICE|DESIGN|API|SECURITY|CEO|PM|DEVOPS))\s*[—\-:]\s*/) ||
              logLine.match(/(?:^|\s)([A-Z][A-Z\s]*(?:OFFICE|DESIGN|API|SECURITY|CEO|PM|DEVOPS))\s*[—\-:]\s*/);

            if (officeMatch) {
              // Extract author from the matched pattern
              author = officeMatch[1].trim();
              avatar = author.slice(0, 2).toUpperCase();
              // Remove the prefix from the content to avoid repetition
              logLine = logLine.replace(officeMatch[0], "").trim();
            } else {
              // Fallback: look for bracketed names or any ALL_CAPS word
              const fallbackMatch = logLine.match(/\[([A-Z][A-Z_]+)\]/) ||
                logLine.match(/\b(CEO|PM|DEVOPS|DESIGN|API|SECURITY)\b/);
              if (fallbackMatch) {
                author = fallbackMatch[1].trim();
                avatar = author.slice(0, 2).toUpperCase();
              } else {
                // Default to System for other messages
                author = "System";
                avatar = "SY";
              }
            }
          }

          set((state) => ({
            agentMessages: [
              ...state.agentMessages,
              {
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author,
                avatar,
                content: logLine,
                timestamp: new Date(),
                isUser: false,
              },
            ],
            terminalLogs: [...state.terminalLogs, terminalLine],
          }));
        }

        // Handle raw terminal output
        if (msg.type === "terminal" && typeof msg.data === "string") {
          const terminalLine = msg.data;
          set((state) => ({
            terminalLogs: [...state.terminalLogs, terminalLine],
          }));
        }

        // Direct Helios site-generator artifact stream.
        if (msg.type === "artifact") {
          const payload = artifactPayload(msg);
          set((state) => upsertArtifactState(state, payload, "helios"));
        }

        // Handle file information
        if (msg.type === "file" && isRecord(msg.data)) {
          const filename = nonEmptyString(msg.data.filename);
          if (filename) {
            set((state) => ({
              projectFiles: state.projectFiles.includes(filename)
                ? state.projectFiles
                : [...state.projectFiles, filename],
            }));
          }
        }

        // Handle per-call token usage (streamed from backend)
        if (msg.type === "token_usage" && isRecord(msg.data)) {
          const inputTokens = msg.data.input_tokens;
          const outputTokens = msg.data.output_tokens;
          const costUsd = msg.data.cost_usd;
          const latencySeconds = msg.data.latency_s;
          if (
            typeof inputTokens === "number" && Number.isFinite(inputTokens)
            && typeof outputTokens === "number" && Number.isFinite(outputTokens)
            && typeof costUsd === "number" && Number.isFinite(costUsd)
            && typeof latencySeconds === "number" && Number.isFinite(latencySeconds)
          ) {
            const newEntry: TokenUsageEntry = {
              office: nonEmptyString(msg.data.office) ?? "unknown",
              input_tokens: inputTokens,
              output_tokens: outputTokens,
              cost_usd: costUsd,
              latency_s: latencySeconds,
              timestamp: Date.now(),
            };
            set((state) => {
              const newLog = [...state.tokenUsageLog, newEntry];
              return {
                tokenUsageLog: newLog,
                costSummary: appendCostSummary(state.costSummary, newEntry),
              };
            });
          }
        }

        // Handle cost optimizer text updates
        if (msg.type === "cost_update" && typeof msg.data === "string") {
          const costMessage = msg.data;
          set((state) => ({
            costMessages: [...state.costMessages, costMessage],
          }));
        }

        // Handle completion
        if (msg.type === "complete") {
          const files = Array.isArray(msg.files)
            ? msg.files.filter((file): file is string => typeof file === "string")
            : undefined;
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}`,
                author: "Helios",
                avatar: "HE",
                content: typeof msg.data === "string" ? msg.data : "Generation complete.",
                timestamp: new Date(),
                isUser: false,
              },
            ],
            projectGithubUrl: nonEmptyString(msg.githubUrl) ?? null,
            projectName: nonEmptyString(msg.projectName) ?? null,
            projectFiles: files
              ? Array.from(new Set([...state.projectFiles, ...files]))
              : state.projectFiles,
          }));
        }

        // Handle errors
        if (msg.type === "error") {
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}`,
                author: "Helios",
                avatar: "HE",
                content: typeof msg.data === "string" ? msg.data : "The site generator reported an error.",
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
        }
      });

      ws.addEventListener("close", () => {
        if (_ws !== ws) return;
        console.log("[ml-service] disconnected");
        cleanup(ws);
        set({ connected: false });

        if (!_shouldReconnect) return;

        // Attempt to reconnect after 3 seconds. Explicit disconnects clear the
        // intent flag, and stale sockets cannot schedule a competing client.
        clearReconnectTimer();
        _reconnectTimer = setTimeout(() => {
          _reconnectTimer = null;
          if (!_shouldReconnect || _ws) return;
          console.log("[ml-service] attempting reconnect…");
          get().connect(url);
        }, 3000);
      });

      ws.addEventListener("error", (err) => {
        if (_ws !== ws) return;
        console.error("[ml-service] WebSocket error", err);
      });
    } catch (err) {
      console.error("[ml-service] failed to connect", err);
    }
  },

  /* ---- disconnect ---- */

  disconnect() {
    _shouldReconnect = false;
    clearReconnectTimer();
    _pendingPrompts.length = 0;
    const websocket = _ws;
    cleanup(websocket);
    websocket?.close();
    set({ connected: false, wrappers: {} });
  },
}));

/* ------------------------------------------------------------------ */
/*  Cleanup helper                                                     */
/* ------------------------------------------------------------------ */

function cleanup(websocket: WebSocket | null = _ws) {
  if (websocket && _ws !== websocket) return;
  if (!websocket || _ws === websocket) {
    _ws = null;
  }
}
