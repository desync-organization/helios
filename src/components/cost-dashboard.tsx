"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  DollarSign,
  Zap,
  Clock,
  BarChart3,
  ArrowDown,
  ArrowUp,
  Activity,
  TrendingDown,
  Layers,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useOrchestratorStore } from "@/lib/orchestrator-store";
import type { TokenUsageEntry, CostSummary } from "@/lib/orchestrator-store";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/**
 * Format a USD amount for display.
 * Shows 6 decimal places for small costs, 4 for larger amounts.
 */
function formatCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(6)}`;
  if (usd < 1) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

/** Format token count with commas. */
function formatTokens(n: number): string {
  return n.toLocaleString();
}

/** Get a color class for an office name. */
function officeColor(office: string): string {
  const colorMap: Record<string, string> = {
    CEO: "text-yellow-400",
    PRODUCT_MANAGER: "text-purple-400",
    ARCHITECT: "text-blue-400",
    COST_OPTIMIZER: "text-emerald-400",
    UI_DESIGNER: "text-pink-400",
    API_DESIGNER: "text-orange-400",
    FRONTEND: "text-cyan-400",
    BACKEND: "text-green-400",
    DATABASE: "text-amber-400",
    QA_ENGINEER: "text-lime-400",
    SECURITY: "text-red-400",
    TECH_WRITER: "text-gray-400",
  };

  const upper = office.toUpperCase();
  for (const [key, color] of Object.entries(colorMap)) {
    if (upper.includes(key)) return color;
  }
  return "text-muted-foreground";
}

/** Derive a short label from an office name. */
function shortOffice(office: string): string {
  return office
    .replace(/[(\[].*[)\]]/g, "")
    .replace(/-retry/g, "")
    .trim()
    .split(" ")[0]
    || office;
}

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  accentClass?: string;
}

function StatCard({ title, value, subtitle, icon, trend, accentClass }: StatCardProps) {
  return (
    <Card className="bg-card/80 backdrop-blur-sm border-border/50">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
              {title}
            </p>
            <p className={cn("text-2xl font-bold tabular-nums", accentClass)}>
              {value}
            </p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className="p-2 rounded-lg bg-muted/50">{icon}</div>
        </div>
        {trend && trend !== "neutral" && (
          <div className="mt-2 flex items-center gap-1">
            {trend === "down" ? (
              <ArrowDown className="w-3 h-3 text-emerald-400" />
            ) : (
              <ArrowUp className="w-3 h-3 text-amber-400" />
            )}
            <span
              className={cn(
                "text-xs",
                trend === "down" ? "text-emerald-400" : "text-amber-400",
              )}
            >
              {trend === "down" ? "Under budget" : "Over estimate"}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Token Bar — visualises token split per office                      */
/* ------------------------------------------------------------------ */

function TokenBar({
  entries,
  totalTokens,
}: {
  entries: { office: string; tokens: number }[];
  totalTokens: number;
}) {
  if (totalTokens === 0) return null;

  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-3 rounded-full overflow-hidden bg-muted/30">
        {entries.map((e, i) => {
          const pct = (e.tokens / totalTokens) * 100;
          if (pct < 0.5) return null;

          return (
            <Tooltip key={i}>
              <TooltipTrigger asChild>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.6, delay: i * 0.05 }}
                  className={cn(
                    "h-full",
                    i % 6 === 0 && "bg-cyan-500",
                    i % 6 === 1 && "bg-emerald-500",
                    i % 6 === 2 && "bg-amber-500",
                    i % 6 === 3 && "bg-purple-500",
                    i % 6 === 4 && "bg-pink-500",
                    i % 6 === 5 && "bg-blue-500",
                  )}
                />
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs font-medium">{shortOffice(e.office)}</p>
                <p className="text-xs text-muted-foreground">
                  {formatTokens(e.tokens)} tokens ({pct.toFixed(1)}%)
                </p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}

/* ------------------------------------------------------------------ */
/*  Per-Office Table                                                    */
/* ------------------------------------------------------------------ */

function OfficeTable({ entries }: { entries: TokenUsageEntry[] }) {
  // Group by office
  const grouped: Record<
    string,
    { calls: number; input: number; output: number; cost: number; latency: number }
  > = {};

  for (const e of entries) {
    const key = shortOffice(e.office);
    if (!grouped[key]) {
      grouped[key] = { calls: 0, input: 0, output: 0, cost: 0, latency: 0 };
    }
    grouped[key].calls += 1;
    grouped[key].input += e.input_tokens;
    grouped[key].output += e.output_tokens;
    grouped[key].cost += e.cost_usd;
    grouped[key].latency += e.latency_s;
  }

  const rows = Object.entries(grouped).sort((a, b) => b[1].cost - a[1].cost);

  if (rows.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
        No token data yet — run a pipeline to see per-office costs.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border/50 text-xs text-muted-foreground uppercase tracking-wider">
            <th className="text-left py-2 px-3">Office</th>
            <th className="text-right py-2 px-3">Calls</th>
            <th className="text-right py-2 px-3">Input</th>
            <th className="text-right py-2 px-3">Output</th>
            <th className="text-right py-2 px-3">Cost</th>
            <th className="text-right py-2 px-3">Avg Latency</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([office, stats]) => (
            <motion.tr
              key={office}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="border-b border-border/30 hover:bg-muted/20 transition-colors"
            >
              <td className="py-2 px-3">
                <span className={cn("font-medium", officeColor(office))}>
                  {office}
                </span>
              </td>
              <td className="text-right py-2 px-3 tabular-nums">{stats.calls}</td>
              <td className="text-right py-2 px-3 tabular-nums text-blue-400">
                {formatTokens(stats.input)}
              </td>
              <td className="text-right py-2 px-3 tabular-nums text-emerald-400">
                {formatTokens(stats.output)}
              </td>
              <td className="text-right py-2 px-3 tabular-nums text-amber-400 font-medium">
                {formatCost(stats.cost)}
              </td>
              <td className="text-right py-2 px-3 tabular-nums text-muted-foreground">
                {stats.calls > 0 ? `${(stats.latency / stats.calls).toFixed(1)}s` : "—"}
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Live Feed — streaming token events                                 */
/* ------------------------------------------------------------------ */

function LiveFeed({ entries }: { entries: TokenUsageEntry[] }) {
  const recent = entries.slice(-30).reverse();

  if (recent.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-muted-foreground gap-2">
        <Activity className="w-6 h-6" />
        <span className="text-sm">Waiting for LLM calls…</span>
      </div>
    );
  }

  return (
    <div className="space-y-1.5 max-h-[400px] overflow-y-auto pr-1">
      <AnimatePresence initial={false}>
        {recent.map((entry, i) => (
          <motion.div
            key={`${entry.office}-${entry.timestamp}-${i}`}
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-3 text-xs bg-muted/30 rounded-lg px-3 py-2"
          >
            <div
              className={cn(
                "w-2 h-2 rounded-full shrink-0",
                entry.cost_usd > 0.001 ? "bg-amber-400" : "bg-emerald-400",
              )}
            />
            <span className={cn("font-medium min-w-[100px]", officeColor(entry.office))}>
              {shortOffice(entry.office)}
            </span>
            <span className="text-blue-400 tabular-nums">
              {formatTokens(entry.input_tokens)} in
            </span>
            <span className="text-muted-foreground">/</span>
            <span className="text-emerald-400 tabular-nums">
              {formatTokens(entry.output_tokens)} out
            </span>
            <span className="flex-1" />
            <span className="text-amber-400 tabular-nums font-medium">
              {formatCost(entry.cost_usd)}
            </span>
            <span className="text-muted-foreground tabular-nums">
              {entry.latency_s.toFixed(1)}s
            </span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Efficiency Card                                                    */
/* ------------------------------------------------------------------ */

function EfficiencyCard({ summary }: { summary: CostSummary }) {
  const totalTokens = summary.totalInputTokens + summary.totalOutputTokens;
  const avgCostPerCall =
    summary.totalCalls > 0
      ? summary.totalCostUsd / summary.totalCalls
      : 0;

  const inputRatio =
    totalTokens > 0
      ? ((summary.totalInputTokens / totalTokens) * 100).toFixed(1)
      : "0";
  const outputRatio =
    totalTokens > 0
      ? ((summary.totalOutputTokens / totalTokens) * 100).toFixed(1)
      : "0";

  return (
    <Card className="bg-card/80 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <TrendingDown className="w-4 h-4 text-emerald-400" />
          Efficiency Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Avg cost/call</p>
            <p className="text-lg font-bold tabular-nums text-amber-400">
              {formatCost(avgCostPerCall)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Token I/O split</p>
            <p className="text-lg font-bold tabular-nums">
              <span className="text-blue-400">{inputRatio}%</span>
              {" / "}
              <span className="text-emerald-400">{outputRatio}%</span>
            </p>
          </div>
        </div>

        <Separator className="bg-border/30" />

        <div>
          <p className="text-xs text-muted-foreground mb-2">
            Token distribution by office
          </p>
          <TokenBar
            entries={summary.perOffice.map((o) => ({
              office: o.office,
              tokens: o.inputTokens + o.outputTokens,
            }))}
            totalTokens={totalTokens}
          />
          <div className="flex flex-wrap gap-2 mt-2">
            {summary.perOffice.slice(0, 6).map((o, i) => (
              <Badge
                key={o.office}
                variant="outline"
                className={cn(
                  "text-[10px]",
                  i % 6 === 0 && "border-cyan-500/30 text-cyan-400",
                  i % 6 === 1 && "border-emerald-500/30 text-emerald-400",
                  i % 6 === 2 && "border-amber-500/30 text-amber-400",
                  i % 6 === 3 && "border-purple-500/30 text-purple-400",
                  i % 6 === 4 && "border-pink-500/30 text-pink-400",
                  i % 6 === 5 && "border-blue-500/30 text-blue-400",
                )}
              >
                {shortOffice(o.office)}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function CostDashboard() {
  const tokenUsageLog = useOrchestratorStore((s) => s.tokenUsageLog);
  const costSummary = useOrchestratorStore((s) => s.costSummary);

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold">Cost Optimizer</h2>
          <Badge variant="secondary" className="text-xs gap-1">
            <DollarSign className="w-3 h-3" />
            Token & Cost Tracking
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn(
              "text-xs tabular-nums",
              costSummary.totalCalls > 0
                ? "border-emerald-400/30 text-emerald-400"
                : "border-muted",
            )}
          >
            {costSummary.totalCalls} calls
          </Badge>
          <Badge
            variant="outline"
            className="text-xs tabular-nums border-amber-400/30 text-amber-400"
          >
            {formatCost(costSummary.totalCostUsd)}
          </Badge>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Top stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            title="Total Cost"
            value={formatCost(costSummary.totalCostUsd)}
            subtitle={`${costSummary.totalCalls} API calls`}
            icon={<DollarSign className="w-5 h-5 text-amber-400" />}
            accentClass="text-amber-400"
          />
          <StatCard
            title="Input Tokens"
            value={formatTokens(costSummary.totalInputTokens)}
            subtitle="Prompt tokens sent"
            icon={<ArrowUp className="w-5 h-5 text-blue-400" />}
            accentClass="text-blue-400"
          />
          <StatCard
            title="Output Tokens"
            value={formatTokens(costSummary.totalOutputTokens)}
            subtitle="Completion tokens received"
            icon={<ArrowDown className="w-5 h-5 text-emerald-400" />}
            accentClass="text-emerald-400"
          />
          <StatCard
            title="Total Tokens"
            value={formatTokens(
              costSummary.totalInputTokens + costSummary.totalOutputTokens,
            )}
            subtitle={`${costSummary.perOffice.length} offices tracked`}
            icon={<Layers className="w-5 h-5 text-purple-400" />}
            accentClass="text-purple-400"
          />
        </div>

        {/* Main tabs */}
        <Tabs defaultValue="breakdown" className="space-y-3">
          <TabsList className="w-fit">
            <TabsTrigger value="breakdown" className="gap-1.5">
              <BarChart3 className="w-3.5 h-3.5" />
              Breakdown
            </TabsTrigger>
            <TabsTrigger value="live" className="gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              Live Feed
            </TabsTrigger>
            <TabsTrigger value="efficiency" className="gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              Efficiency
            </TabsTrigger>
          </TabsList>

          <TabsContent value="breakdown">
            <Card className="bg-card/80 backdrop-blur-sm border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Per-Office Cost Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                <OfficeTable entries={tokenUsageLog} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="live">
            <Card className="bg-card/80 backdrop-blur-sm border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  Real-Time Token Stream
                  {tokenUsageLog.length > 0 && (
                    <motion.span
                      animate={{ opacity: [1, 0.4] }}
                      transition={{ duration: 1, repeat: Infinity }}
                      className="w-2 h-2 rounded-full bg-emerald-400"
                    />
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <LiveFeed entries={tokenUsageLog} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="efficiency">
            <EfficiencyCard summary={costSummary} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
