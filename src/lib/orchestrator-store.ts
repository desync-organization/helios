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

/* ------------------------------------------------------------------ */
/*  Singleton WebSocket bookkeeping (outside Zustand to avoid cycles)  */
/* ------------------------------------------------------------------ */

let _ws: WebSocket | null = null;
let _heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let _statusPollTimer: ReturnType<typeof setInterval> | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _registeredId: string | null = null;

/** Fetch /status via HTTP to get the wrapper list (fallback & periodic sync). */
async function pollWrapperStatus(httpUrl: string) {
  try {
    const res = await fetch(httpUrl);
    if (!res.ok) return;
    const data = (await res.json()) as { wrappers: WrapperInfo[] };
    const map: Record<string, WrapperInfo> = {};
    for (const w of data.wrappers) {
      // Hide our own UI observer from the wrapper list
      if (w.id === _registeredId) continue;
      map[w.id] = w;
    }
    useOrchestratorStore.setState({ wrappers: map });
  } catch {
    /* orchestrator might be down – ignore */
  }
}

/** Recompute the cost summary from the full token usage log. */
function _recomputeCostSummary(log: TokenUsageEntry[]): CostSummary {
  let totalIn = 0;
  let totalOut = 0;
  let totalCost = 0;
  const perOfficeMap: Record<string, PerOfficeStat> = {};

  for (const entry of log) {
    totalIn += entry.input_tokens;
    totalOut += entry.output_tokens;
    totalCost += entry.cost_usd;

    // Derive short office name for grouping
    const officeKey = entry.office
      .replace(/[(\[].*[)\]]/g, "")
      .replace(/-retry/g, "")
      .trim()
      .split(" ")[0] || entry.office;

    if (!perOfficeMap[officeKey]) {
      perOfficeMap[officeKey] = {
        office: officeKey,
        calls: 0,
        inputTokens: 0,
        outputTokens: 0,
        costUsd: 0,
        totalLatency: 0,
      };
    }
    perOfficeMap[officeKey].calls += 1;
    perOfficeMap[officeKey].inputTokens += entry.input_tokens;
    perOfficeMap[officeKey].outputTokens += entry.output_tokens;
    perOfficeMap[officeKey].costUsd += entry.cost_usd;
    perOfficeMap[officeKey].totalLatency += entry.latency_s;
  }

  return {
    totalInputTokens: totalIn,
    totalOutputTokens: totalOut,
    totalCostUsd: Math.round(totalCost * 1e6) / 1e6,
    totalCalls: log.length,
    perOffice: Object.values(perOfficeMap).sort((a, b) => b.costUsd - a.costUsd),
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
    // 1) Echo locally so the UI feels responsive immediately
    set((state) => ({
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

    // 2) Send prompt directly to ML service
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({ type: 'prompt', data: text }));
    }
  },

  /* ---- connect to the orchestrator WebSocket ---- */

  connect(url: string) {
    // Prevent duplicate connections
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      _ws = ws;

      ws.addEventListener("open", () => {
        console.log("[ml-service] connected to", url);
        set({ connected: true });
      });

      ws.addEventListener("message", (event) => {
        let msg: { type: string; data: string; githubUrl?: string; projectName?: string };
        try {
          msg = JSON.parse(String(event.data));
        } catch {
          console.warn("[ml-service] invalid message", event.data);
          return;
        }

        // Handle progress updates
        if (msg.type === 'progress') {
          let logLine = msg.data;

          // Only show "ML Pipeline" as author for the starting message
          // Otherwise extract office name from content (e.g., "🏢 CEO OFFICE" -> "CEO OFFICE")
          let author = 'ML Pipeline';
          let avatar = 'ML';

          if (!logLine.includes('Starting ML pipeline for:')) {
            // Try to extract office name from patterns like "🏢 CEO OFFICE — ..." or "⚡️ DEVOPS OFFICE — ..."
            // Match at start of line OR after whitespace, with optional emoji prefix
            const officeMatch = logLine.match(/^(?:[🏢⚡️✅⏳🔧🚀📁🔗📤📝❌⚠️])?\s*([A-Z][A-Z\s]*(?:OFFICE|DESIGN|API|SECURITY|CEO|PM|DEVOPS))\s*[—\-:]\s*/) ||
              logLine.match(/(?:^|\s)([A-Z][A-Z\s]*(?:OFFICE|DESIGN|API|SECURITY|CEO|PM|DEVOPS))\s*[—\-:]\s*/);

            if (officeMatch) {
              // Extract author from the matched pattern
              author = officeMatch[1].trim();
              avatar = author.slice(0, 2).toUpperCase();
              // Remove the prefix from the content to avoid repetition
              logLine = logLine.replace(officeMatch[0], '').trim();
            } else {
              // Fallback: look for bracketed names or any ALL_CAPS word
              const fallbackMatch = logLine.match(/\[([A-Z][A-Z_]+)\]/) ||
                logLine.match(/\b(CEO|PM|DEVOPS|DESIGN|API|SECURITY)\b/);
              if (fallbackMatch) {
                author = fallbackMatch[1].trim();
                avatar = author.slice(0, 2).toUpperCase();
              } else {
                // Default to System for other messages
                author = 'System';
                avatar = 'SY';
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
            terminalLogs: [...state.terminalLogs, msg.data], // Keep original in terminal
          }));
        }

        // Handle raw terminal output
        if (msg.type === 'terminal') {
          set((state) => ({
            terminalLogs: [...state.terminalLogs, msg.data],
          }));
        }

        // Handle file information
        if (msg.type === 'file') {
          const fileData = (msg as any).data as { filename: string; language: string; path: string };
          set((state) => ({
            projectFiles: [...state.projectFiles, fileData.filename],
          }));
        }

        // Handle per-call token usage (streamed from backend)
        if (msg.type === 'token_usage') {
          const entry = msg.data as unknown as TokenUsageEntry;
          if (entry && typeof entry.input_tokens === 'number') {
            const newEntry: TokenUsageEntry = {
              office: entry.office ?? 'unknown',
              input_tokens: entry.input_tokens,
              output_tokens: entry.output_tokens,
              cost_usd: entry.cost_usd,
              latency_s: entry.latency_s,
              timestamp: Date.now(),
            };
            set((state) => {
              const newLog = [...state.tokenUsageLog, newEntry];
              return {
                tokenUsageLog: newLog,
                costSummary: _recomputeCostSummary(newLog),
              };
            });
          }
        }

        // Handle cost optimizer text updates
        if (msg.type === 'cost_update') {
          set((state) => ({
            costMessages: [...state.costMessages, msg.data],
          }));
        }

        // Handle completion
        if (msg.type === 'complete') {
          const files = (msg as any).files as string[] | undefined;
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}`,
                author: 'Helios',
                avatar: 'GR',
                content: msg.data,
                timestamp: new Date(),
                isUser: false,
              },
            ],
            projectGithubUrl: msg.githubUrl || null,
            projectName: msg.projectName || null,
            projectFiles: files || state.projectFiles,
          }));
        }

        // Handle errors
        if (msg.type === 'error') {
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}`,
                author: 'Helios',
                avatar: 'GR',
                content: msg.data,
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
        }
      });

      ws.addEventListener("close", () => {
        console.log("[ml-service] disconnected");
        cleanup();
        set({ connected: false });

        // Attempt to reconnect after 3 seconds
        if (_reconnectTimer) clearTimeout(_reconnectTimer);
        _reconnectTimer = setTimeout(() => {
          console.log("[ml-service] attempting reconnect…");
          get().connect(url);
        }, 3000);
      });

      ws.addEventListener("error", (err) => {
        console.error("[ml-service] WebSocket error", err);
      });
    } catch (err) {
      console.error("[ml-service] failed to connect", err);
    }
  },

  /* ---- disconnect ---- */

  disconnect() {
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer);
      _reconnectTimer = null;
    }
    if (_ws) {
      // Send graceful shutdown
      try {
        _ws.send(
          JSON.stringify({
            type: "SHUTDOWN",
            src: _registeredId ?? "ui-observer",
            ts: Date.now(),
          }),
        );
      } catch { /* ignore */ }
      _ws.close();
    }
    cleanup();
    set({ connected: false, wrappers: {} });
  },
}));

/* ------------------------------------------------------------------ */
/*  Cleanup helper                                                     */
/* ------------------------------------------------------------------ */

function cleanup() {
  if (_heartbeatTimer) {
    clearInterval(_heartbeatTimer);
    _heartbeatTimer = null;
  }
  if (_statusPollTimer) {
    clearInterval(_statusPollTimer);
    _statusPollTimer = null;
  }
  _ws = null;
}

/* ------------------------------------------------------------------ */
/*  Envelope handler – routes incoming messages to state updates       */
/* ------------------------------------------------------------------ */

function handleEnvelope(
  env: Envelope,
  set: (partial: Partial<OrchestratorState> | ((s: OrchestratorState) => Partial<OrchestratorState>)) => void,
  get: () => OrchestratorState,
) {
  const payload = (env.payload ?? {}) as Record<string, unknown>;

  switch (env.type) {
    /* ---- Registration acknowledgement ---- */
    case "REGISTER_ACK": {
      _registeredId = (payload.id as string) ?? env.id ?? "ui-observer";
      console.log("[orchestrator] registered as", _registeredId);
      break;
    }

    /* ---- Heartbeat ack — silently consumed ---- */
    case "HEARTBEAT_ACK":
      break;

    /* ---- EVENT envelope — the main message bus ---- */
    case "EVENT": {
      const kind = payload.kind as string | undefined;

      switch (kind) {
        /* PM responding to a user chat message */
        case "CHAT_RESPONSE": {
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author: payload.author as string ?? "Helios PM",
                avatar: "PM",
                content: (payload.text as string) ?? (payload.message as string) ?? "",
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        /* Agent-to-agent or agent-to-UI summary messages */
        case "AGENT_MESSAGE": {
          set((state) => ({
            agentMessages: [
              ...state.agentMessages,
              {
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author: (payload.author as string) ?? env.src ?? "Agent",
                avatar: ((payload.author as string) ?? env.src ?? "AG").slice(0, 2).toUpperCase(),
                content: (payload.text as string) ?? (payload.message as string) ?? "",
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        /* A specialist generated a code artifact */
        case "CODE_ARTIFACT": {
          const artifactId =
            (payload.id as string) ??
            `art-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
          const filename = (payload.filename as string) ?? "untitled";
          const language = (payload.language as string) ?? "typescript";
          const code = (payload.code as string) ?? "";
          const artType = (payload.artifactType as string) ?? (payload.type as string) ?? "component";
          const componentName = (payload.componentName as string) ?? undefined;
          const wrapper = env.src ?? "unknown";
          const progress = (payload.progress as number) ?? 100;
          const status = progress >= 100 ? "complete" : "streaming";

          set((state) => {
            const existing = state.artifacts.findIndex((a) => a.id === artifactId);
            let newArtifacts: CodeArtifact[];

            if (existing >= 0) {
              // Update existing artifact (streaming progress)
              newArtifacts = [...state.artifacts];
              newArtifacts[existing] = {
                ...newArtifacts[existing],
                code,
                progress,
                status,
              };
            } else {
              // New artifact
              newArtifacts = [
                ...state.artifacts,
                {
                  id: artifactId,
                  filename,
                  language,
                  code,
                  type: artType,
                  wrapper,
                  agent: wrapper,
                  timestamp: new Date(),
                  status,
                  progress,
                  componentName,
                },
              ];
            }

            return {
              artifacts: newArtifacts,
              // Auto-select the first artifact if none selected
              activeArtifactId: state.activeArtifactId ?? artifactId,
            };
          });
          break;
        }

        /* PM signals that the full project is ready (GitHub repo created) */
        case "PROJECT_READY": {
          set({
            projectGithubUrl: (payload.githubUrl as string) ?? (payload.url as string) ?? null,
            projectName: (payload.projectName as string) ?? null,
            projectRepoName: (payload.repoName as string) ?? null,
          });
          // Add a chat message informing the user
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-project-${Date.now()}`,
                author: "Helios PM",
                avatar: "PM",
                content: `🎉 Project is ready! ${(payload.githubUrl as string) ?? "Check the Workstation for generated code."}`,
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        /* Status update from a wrapper */
        case "STATUS_UPDATE": {
          const wrapperId = env.src;
          if (wrapperId) {
            set((state) => {
              const existing = state.wrappers[wrapperId];
              if (!existing) return {};
              return {
                wrappers: {
                  ...state.wrappers,
                  [wrapperId]: {
                    ...existing,
                    status: (payload.status as WrapperStatus) ?? existing.status,
                    lastSeen: Date.now(),
                  },
                },
              };
            });
          }
          break;
        }

        /* Legacy specialist outputs — treat as agent messages */
        case "DESIGN_DRAFT":
        case "API_DRAFT":
        case "SCHEMA_DRAFT":
        case "AUDIT_REPORT":
        case "POLICY_RESULT": {
          set((state) => ({
            agentMessages: [
              ...state.agentMessages,
              {
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author: env.src ?? "Specialist",
                avatar: (env.src ?? "SP").slice(0, 2).toUpperCase(),
                content: (payload.summary as string) ?? (payload.text as string) ?? JSON.stringify(payload).slice(0, 300),
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        default:
          console.log("[orchestrator] unhandled EVENT kind:", kind, payload);
      }
      break;
    }

    /* ---- Catch-all for other envelope types (CHAT_RESPONSE at top level etc.) ---- */
    default: {
      // Some messages may arrive at top-level (not wrapped in EVENT)
      if (env.type === "CHAT_RESPONSE") {
        set((state) => ({
          chatMessages: [
            ...state.chatMessages,
            {
              id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              author: (payload.author as string) ?? "Helios PM",
              avatar: "PM",
              content: (payload.text as string) ?? (payload.message as string) ?? "",
              timestamp: new Date(),
              isUser: false,
            },
          ],
        }));
      } else if (env.type === "AGENT_MESSAGE") {
        set((state) => ({
          agentMessages: [
            ...state.agentMessages,
            {
              id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              author: (payload.author as string) ?? env.src ?? "Agent",
              avatar: ((payload.author as string) ?? env.src ?? "AG").slice(0, 2).toUpperCase(),
              content: (payload.text as string) ?? (payload.message as string) ?? "",
              timestamp: new Date(),
              isUser: false,
            },
          ],
        }));
      } else {
        console.log("[orchestrator] unhandled envelope:", env.type, env);
      }
    }
  }
}
