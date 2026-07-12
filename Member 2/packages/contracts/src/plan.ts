import { z } from "zod";
import { EpochMs, ShortText, externalObject } from "./common";
import { ArtifactId, RunId, TaskId } from "./ids";

export const PlanNode = z.object({
  nodeId: z.string().regex(/^node_[A-Za-z0-9_-]{1,80}$/),
  role: ShortText,
  dependsOn: z.array(z.string().regex(/^node_[A-Za-z0-9_-]{1,80}$/)).max(50),
  acceptanceCriteria: z.array(z.string().min(1).max(1_024)).min(1).max(30),
  toolGrants: z.array(ShortText).max(30),
  budget: z.object({ timeoutMs: z.number().int().min(100).max(3_600_000), maxTokens: z.number().int().min(1).max(1_000_000), maxCostUsd: z.number().nonnegative().max(10_000) }).strict(),
}).strict();

export const Plan = externalObject({
  artifactId: ArtifactId,
  taskId: TaskId,
  runId: RunId,
  plannerVersion: ShortText,
  nodes: z.array(PlanNode).min(1).max(200),
  createdAt: EpochMs,
}).superRefine((plan, context) => {
  const ids = new Set(plan.nodes.map((node) => node.nodeId));
  if (ids.size !== plan.nodes.length) context.addIssue({ code: "custom", message: "plan node IDs must be unique" });
  for (const node of plan.nodes) for (const dependency of node.dependsOn) if (!ids.has(dependency)) context.addIssue({ code: "custom", message: `missing dependency ${dependency}` });
  const dependencies = new Map(plan.nodes.map((node) => [node.nodeId, node.dependsOn]));
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const hasCycle = (nodeId: string): boolean => {
    if (visiting.has(nodeId)) return true;
    if (visited.has(nodeId)) return false;
    visiting.add(nodeId);
    for (const dependency of dependencies.get(nodeId) ?? []) if (hasCycle(dependency)) return true;
    visiting.delete(nodeId);
    visited.add(nodeId);
    return false;
  };
  if (plan.nodes.some((node) => hasCycle(node.nodeId))) context.addIssue({ code: "custom", message: "plan must be acyclic" });
});

export type Plan = z.infer<typeof Plan>;
