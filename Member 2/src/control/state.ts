import type { WritebackMode } from "../../packages/contracts/src/writeback";

export interface SystemState {
  globalPaused: boolean;
  emergencyMode: boolean;
  pausedAgents: string[];
  writebackMode: WritebackMode;
  securityScanMode: "read-only" | "remediation-approved";
  currentAgentTag: string;
  currentAdapterPointers: Record<string, string>;
  updatedAt: number;
}

export function defaultSystemState(now = Date.now()): SystemState {
  return {
    globalPaused: false,
    emergencyMode: false,
    pausedAgents: [],
    writebackMode: "dry-run",
    securityScanMode: "read-only",
    currentAgentTag: "agents-v1",
    currentAdapterPointers: {},
    updatedAt: now,
  };
}

export class AtomicSystemState {
  private state: SystemState;
  constructor(initial = defaultSystemState()) { this.state = structuredClone(initial); }
  read(): Readonly<SystemState> { return structuredClone(this.state); }
  update(patch: Partial<Omit<SystemState, "updatedAt">>, now = Date.now()): Readonly<SystemState> {
    this.state = { ...this.state, ...structuredClone(patch), updatedAt: now };
    return this.read();
  }
  pauseAgent(agent: string, now = Date.now()): void {
    this.update({ pausedAgents: [...new Set([...this.state.pausedAgents, agent])] }, now);
  }
}
