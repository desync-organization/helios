"use client";

import { useEffect, useCallback, useRef } from "react";
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Edge,
  type Node,
  Handle,
  Position,
} from "@xyflow/react";
import { motion } from "framer-motion";
import {
  Boxes,
  ChartNoAxesCombined,
  Compass,
  Network,
  PanelsTopLeft,
  Rocket,
  ServerCog,
  ShieldCheck,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  useOrchestratorStore,
  type WrapperInfo,
  type WrapperStatus,
} from "@/lib/orchestrator-store";
import "@xyflow/react/dist/style.css";

type OfficeStatus = "idle" | "thinking" | "working" | "blocked";

interface DroneInfo {
  name: string;
  status: OfficeStatus;
}

interface OfficeNodeData {
  label: string;
  status: OfficeStatus;
  type: "head" | "worker";
  role: string;
  drones: DroneInfo[];
  live?: boolean;
  [key: string]: unknown;
}

const statusConfig: Record<OfficeStatus, { color: string; pulse: boolean }> = {
  idle: { color: "bg-zinc-400", pulse: false },
  thinking: { color: "bg-amber-400", pulse: true },
  working: { color: "bg-emerald-400", pulse: true },
  blocked: { color: "bg-red-400", pulse: true },
};

const roleVisuals: Record<
  string,
  { icon: LucideIcon; className: string }
> = {
  Orchestrator: { icon: Network, className: "border-violet-400/35 text-violet-300" },
  "Head Agent": { icon: Network, className: "border-violet-400/35 text-violet-300" },
  Architect: { icon: Compass, className: "border-sky-400/35 text-sky-300" },
  "Frontend Dev": {
    icon: PanelsTopLeft,
    className: "border-cyan-400/35 text-cyan-300",
  },
  "Backend Dev": {
    icon: ServerCog,
    className: "border-blue-400/35 text-blue-300",
  },
  Deployment: { icon: Rocket, className: "border-indigo-400/35 text-indigo-300" },
  Security: {
    icon: ShieldCheck,
    className: "border-rose-400/35 text-rose-300",
  },
  DevOps: { icon: Workflow, className: "border-teal-400/35 text-teal-300" },
  "Cost Optimizer": {
    icon: ChartNoAxesCombined,
    className: "border-amber-400/35 text-amber-300",
  },
  default: { icon: Boxes, className: "border-slate-400/35 text-slate-300" },
};

/** Map backend WrapperInfo.type to a human-friendly role label. */
function wrapperTypeToRole(type: string): string {
  const map: Record<string, string> = {
    "frontend-design": "Frontend Dev",
    health: "DevOps",
    "backend-api": "Backend Dev",
    security: "Security",
    "cost-optimizer": "Cost Optimizer",
  };
  return map[type] ?? type;
}

/** Map backend WrapperStatus enum to lowercase OfficeStatus. */
function toOfficeStatus(ws: WrapperStatus): OfficeStatus {
  return ws.toLowerCase() as OfficeStatus;
}

/* ------------------------------------------------------------------ */
/*  OfficeNode component                                               */
/* ------------------------------------------------------------------ */

function OfficeNode({ data }: { data: OfficeNodeData }) {
  const status = statusConfig[data.status];
  const roleVisual = roleVisuals[data.role] ?? roleVisuals.default;
  const IconComponent = roleVisual.icon;

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        "relative min-w-[220px] max-w-[280px] rounded-xl border bg-card/95 p-4 shadow-xl shadow-black/20 backdrop-blur-sm",
        data.status === "blocked" && "border-red-400/50 shadow-red-400/20",
        data.status === "working" &&
        "border-emerald-400/50 shadow-emerald-400/20",
        data.status === "thinking" && "border-amber-400/50 shadow-amber-400/20",
        data.status === "idle" && "border-border",
      )}
    >
      {/* Live indicator dot */}
      {data.live && (
        <div className="absolute -top-1 -left-1 w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
      )}

      {/* Status Indicator */}
      <div
        className={cn(
          "absolute -top-2 -right-2 w-4 h-4 rounded-full border-2 border-card",
          status.color,
          status.pulse && "animate-pulse",
        )}
      />

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400"
      />

      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "grid h-10 w-10 shrink-0 place-items-center rounded-lg border bg-background/70 shadow-inner shadow-black/20",
            roleVisual.className,
          )}
        >
          <IconComponent className="h-5 w-5" strokeWidth={1.8} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{data.label}</h3>
          <p className="text-xs text-muted-foreground">{data.role}</p>
        </div>
      </div>

      {/* Drones List */}
      {data.drones && data.drones.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {data.drones.map((drone, idx) => {
            const droneStatus = statusConfig[drone.status];
            return (
              <div
                key={idx}
                className="flex items-center gap-2 text-xs bg-muted/50 rounded px-2 py-1"
              >
                <div
                  className={cn(
                    "w-2 h-2 rounded-full shrink-0",
                    droneStatus.color,
                    droneStatus.pulse && "animate-pulse",
                  )}
                />
                <span className="truncate text-muted-foreground">
                  {drone.name}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Stats Badge */}
      <div className="mt-3 flex items-center gap-2">
        <Badge
          variant="outline"
          className={cn(
            "text-xs capitalize",
            data.status === "working" &&
            "border-emerald-400/30 text-emerald-400",
            data.status === "thinking" && "border-amber-400/30 text-amber-400",
            data.status === "blocked" && "border-red-400/30 text-red-400",
          )}
        >
          {data.status}
        </Badge>
      </div>

      {/* Output Handles */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="code"
        className="!w-3 !h-3 !bg-emerald-400"
        style={{ left: "30%" }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="data"
        className="!w-3 !h-3 !bg-blue-400"
        style={{ left: "50%" }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="error"
        className="!w-3 !h-3 !bg-red-400"
        style={{ left: "70%" }}
      />
    </motion.div>
  );
}

const nodeTypes = { office: OfficeNode };

/* ------------------------------------------------------------------ */
/*  Convert live wrapper map -> React Flow nodes & edges               */
/* ------------------------------------------------------------------ */

const ORCHESTRATOR_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "ws://localhost:9100")
    : "ws://localhost:9100";

/** Layout helpers to auto-place wrappers in a grid. */
function buildLiveGraph(wrappers: Record<string, WrapperInfo>): {
  nodes: Node<OfficeNodeData>[];
  edges: Edge[];
} {
  const entries = Object.values(wrappers).filter(
    (w) => w.type !== "ui-observer",
  );

  if (entries.length === 0) return { nodes: DEMO_NODES, edges: DEMO_EDGES };

  // Place an "orchestrator hub" node at top centre
  const hubNode: Node<OfficeNodeData> = {
    id: "orchestrator-hub",
    type: "office",
    position: { x: 400, y: 80 },
    data: {
      label: "Orchestrator",
      status: "working",
      type: "head",
      role: "Head Agent",
      drones: Array.from({ length: Math.max(1, entries.length) }).map(
        (_, idx) => ({
          name: `Agent ${idx + 1}`,
          status: "working",
        }),
      ),
      live: true,
    },
  };

  const spacing = 280;
  const startX = 400 - ((entries.length - 1) * spacing) / 2;

  const nodes: Node<OfficeNodeData>[] = [hubNode];
  const edges: Edge[] = [];

  entries.forEach((w, i) => {
    nodes.push({
      id: w.id,
      type: "office",
      position: { x: startX + i * spacing, y: 320 },
      data: {
        label: w.meta.name,
        status: toOfficeStatus(w.status),
        type: "worker",
        role: wrapperTypeToRole(w.type),
        drones: Array.isArray((w.meta as any).drones)
          ? ((w.meta as any).drones as DroneInfo[])
          : Array.from({ length: Math.max(1, Number(w.meta.drones ?? 1)) }).map(
            (_, dIdx) => ({
              name: `${wrapperTypeToRole(w.type)} Agent ${dIdx + 1}`,
              status: "idle",
            }),
          ),
        live: true,
      },
    });

    const statusColor: Record<WrapperStatus, string> = {
      IDLE: "#9ca3af",
      THINKING: "#f59e0b",
      WORKING: "#10b981",
      BLOCKED: "#ef4444",
    };

    edges.push({
      id: `e-hub-${w.id}`,
      source: "orchestrator-hub",
      target: w.id,
      animated: w.status !== "IDLE",
      style: { stroke: statusColor[w.status] ?? "#9ca3af" },
    });
  });

  return { nodes, edges };
}

/* ------------------------------------------------------------------ */
/*  Demo fallback data (shown when orchestrator is offline)            */
/* ------------------------------------------------------------------ */

const DEMO_NODES: Node<OfficeNodeData>[] = [
  {
    id: "1",
    type: "office",
    position: { x: 400, y: 50 },
    data: {
      label: "CEO Office",
      status: "idle",
      type: "head",
      role: "Orchestrator",
      drones: [
        { name: "Project Planner", status: "idle" },
        { name: "File Manifest Generator", status: "idle" },
      ],
    },
  },
  {
    id: "2",
    type: "office",
    position: { x: 400, y: 250 },
    data: {
      label: "Product Office",
      status: "idle",
      type: "worker",
      role: "Architect",
      drones: [
        { name: "Tech Stack Selector", status: "idle" },
        { name: "Architecture Designer", status: "idle" },
      ],
    },
  },
  {
    id: "3",
    type: "office",
    position: { x: 150, y: 450 },
    data: {
      label: "Engineering - Frontend",
      status: "idle",
      type: "worker",
      role: "Frontend Dev",
      drones: [
        { name: "Component Builder", status: "idle" },
        { name: "UI Developer", status: "idle" },
      ],
    },
  },
  {
    id: "4",
    type: "office",
    position: { x: 650, y: 450 },
    data: {
      label: "Engineering - Backend",
      status: "idle",
      type: "worker",
      role: "Backend Dev",
      drones: [
        { name: "API Developer", status: "idle" },
        { name: "Logic Engineer", status: "idle" },
      ],
    },
  },
  {
    id: "5",
    type: "office",
    position: { x: 400, y: 650 },
    data: {
      label: "DevOps Office",
      status: "idle",
      type: "worker",
      role: "Deployment",
      drones: [
        { name: "Git Manager", status: "idle" },
        { name: "GitHub Publisher", status: "idle" },
      ],
    },
  },
  {
    id: "6",
    type: "office",
    position: { x: 750, y: 250 },
    data: {
      label: "Cost Optimizer",
      status: "idle",
      type: "worker",
      role: "Cost Optimizer",
      drones: [
        { name: "Token Tracker", status: "idle" },
        { name: "Path Optimizer", status: "idle" },
      ],
    },
  },
];

const DEMO_EDGES: Edge[] = [
  {
    id: "e1-2",
    source: "1",
    target: "2",
    animated: true,
    style: { stroke: "#3b82f6" },
  },
  {
    id: "e2-3",
    source: "2",
    target: "3",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e2-4",
    source: "2",
    target: "4",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e3-5",
    source: "3",
    target: "5",
    animated: true,
    style: { stroke: "#fbbf24" },
  },
  {
    id: "e4-5",
    source: "4",
    target: "5",
    animated: true,
    style: { stroke: "#fbbf24" },
  },
  {
    id: "e2-6",
    source: "2",
    target: "6",
    animated: true,
    style: { stroke: "#f59e0b" },
  },
  {
    id: "e6-5",
    source: "6",
    target: "5",
    animated: true,
    style: { stroke: "#f59e0b" },
  },
];

/* ------------------------------------------------------------------ */
/*  BlueprintCanvas component                                          */
/* ------------------------------------------------------------------ */

export function BlueprintCanvas() {
  const { wrappers, connected, connect, disconnect } = useOrchestratorStore();
  const [nodes, setNodes, onNodesChange] = useNodesState(DEMO_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(DEMO_EDGES);

  // Connect on mount — don't disconnect on unmount (shared WS connection)
  useEffect(() => {
    connect(ORCHESTRATOR_URL);
  }, [connect]);

  // Track previous wrapper keys to detect actual changes
  const prevWrapperKeysRef = useRef<string>("");

  // Rebuild the graph whenever live wrappers actually change
  useEffect(() => {
    const wrapperKeys = Object.keys(wrappers).sort().join(",");
    const wrapperHash =
      wrapperKeys +
      JSON.stringify(Object.values(wrappers).map((w) => `${w.id}-${w.status}`));

    // Only rebuild if wrappers actually changed
    if (prevWrapperKeysRef.current === wrapperHash) return;
    prevWrapperKeysRef.current = wrapperHash;

    const { nodes: liveNodes, edges: liveEdges } = buildLiveGraph(wrappers);
    setNodes(liveNodes);
    setEdges(liveEdges);
  }, [wrappers]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  );

  return (
    <div className="w-full h-full bg-background relative">


      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        className="bg-dot-pattern"
      >
        <Background gap={20} size={1} className="bg-muted/20" />
      </ReactFlow>
    </div>
  );
}
