"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Terminal as TerminalIcon,
  Zap,
  AlertTriangle,
  UserPlus,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useOrchestratorStore } from "@/lib/orchestrator-store";

interface TerminalLine {
  id: string;
  type: "input" | "output" | "error" | "success" | "system";
  content: string;
  timestamp: Date;
}

const initialLines: TerminalLine[] = [
  {
    id: "1",
    type: "system",
    content: "Helios Terminal v3.0.0",
    timestamp: new Date(),
  },
  {
    id: "2",
    type: "system",
    content: "Type /help for available commands",
    timestamp: new Date(),
  },
];

const commandResponses: Record<string, TerminalLine[]> = {
  "/help": [
    {
      id: "h1",
      type: "output",
      content: "Available Commands:",
      timestamp: new Date(),
    },
    {
      id: "h2",
      type: "output",
      content: "  /deploy [--force]  - Deploy the application",
      timestamp: new Date(),
    },
    {
      id: "h3",
      type: "output",
      content: "  /evacuate          - Emergency session restart",
      timestamp: new Date(),
    },
    {
      id: "h4",
      type: "output",
      content: "  /hire [Role]       - Spawn custom agent",
      timestamp: new Date(),
    },
    {
      id: "h5",
      type: "output",
      content: "  /status            - Show system status",
      timestamp: new Date(),
    },
    {
      id: "h6",
      type: "output",
      content: "  /clear             - Clear terminal",
      timestamp: new Date(),
    },
  ],
  "/status": [
    {
      id: "s1",
      type: "output",
      content: "System Status:",
      timestamp: new Date(),
    },
    {
      id: "s2",
      type: "output",
      content: "  Offices Online: 4",
      timestamp: new Date(),
    },
    {
      id: "s3",
      type: "output",
      content: "  Active Drones: 10",
      timestamp: new Date(),
    },
    {
      id: "s4",
      type: "output",
      content: "  Tasks Completed: 47",
      timestamp: new Date(),
    },
    {
      id: "s5",
      type: "success",
      content: "  All systems operational",
      timestamp: new Date(),
    },
  ],
  "/deploy": [
    {
      id: "d1",
      type: "output",
      content: "Initiating deployment sequence...",
      timestamp: new Date(),
    },
    {
      id: "d2",
      type: "output",
      content: "Running tests...",
      timestamp: new Date(),
    },
    {
      id: "d3",
      type: "success",
      content: "All tests passed. Deploying to production...",
      timestamp: new Date(),
    },
    {
      id: "d4",
      type: "success",
      content: "Deployment complete!",
      timestamp: new Date(),
    },
  ],
  "/deploy --force": [
    {
      id: "df1",
      type: "error",
      content: "WARNING: Bypassing tests!",
      timestamp: new Date(),
    },
    {
      id: "df2",
      type: "output",
      content: "Force deploying...",
      timestamp: new Date(),
    },
    {
      id: "df3",
      type: "success",
      content: "Deployment complete (forced).",
      timestamp: new Date(),
    },
  ],
  "/evacuate": [
    {
      id: "e1",
      type: "error",
      content: "EMERGENCY EVACUATION INITIATED",
      timestamp: new Date(),
    },
    {
      id: "e2",
      type: "output",
      content: "Terminating all sessions...",
      timestamp: new Date(),
    },
    {
      id: "e3",
      type: "output",
      content: "Clearing sandboxes...",
      timestamp: new Date(),
    },
    {
      id: "e4",
      type: "success",
      content: "System reset complete. Restarting...",
      timestamp: new Date(),
    },
  ],
};

const lineColors: Record<TerminalLine["type"], string> = {
  input: "text-foreground",
  output: "text-primary",
  error: "text-destructive",
  success: "text-accent",
  system: "text-secondary",
};

const lineIcons: Record<TerminalLine["type"], LucideIcon | null> = {
  input: ChevronRight,
  output: null,
  error: AlertTriangle,
  success: Zap,
  system: TerminalIcon,
};

export function GodModeTerminal() {
  const { terminalLogs, clearTerminal } = useOrchestratorStore();
  const [lines, setLines] = useState<TerminalLine[]>(initialLines);
  const [inputValue, setInputValue] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Function to detect and linkify URLs
  const linkifyContent = (content: string) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = content.split(urlRegex);
    
    return parts.map((part, index) => {
      if (urlRegex.test(part)) {
        return (
          <a
            key={index}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline cursor-pointer"
            onClick={(e) => e.stopPropagation()}
          >
            {part}
          </a>
        );
      }
      return part;
    });
  };

  // Merge terminal logs from ML pipeline with local command output
  const allLines = [
    ...lines,
    ...terminalLogs.map((log, idx) => ({
      id: `ml-${idx}`,
      type: (log.includes('[ERROR]') ? 'error' : 'output') as TerminalLine['type'],
      content: log,
      timestamp: new Date(),
    })),
  ];

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allLines.length]);

  const executeCommand = (cmd: string) => {
    const trimmedCmd = cmd.trim().toLowerCase();

    // Add input line
    const inputLine: TerminalLine = {
      id: Date.now().toString(),
      type: "input",
      content: cmd,
      timestamp: new Date(),
    };

    setLines((prev) => [...prev, inputLine]);
    setHistory((prev) => [...prev, cmd]);
    setHistoryIndex(-1);

    // Handle commands
    if (trimmedCmd === "/clear") {
      setLines([]);
      clearTerminal();
      return;
    }

    const response = commandResponses[trimmedCmd];
    if (response) {
      setTimeout(() => {
        setLines((prev) => [...prev, ...response]);
      }, 100);
    } else if (trimmedCmd.startsWith("/hire")) {
      const role = cmd.slice(5).trim() || "Generic Agent";
      setTimeout(() => {
        setLines((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            type: "success",
            content: `Spawned new ${role} agent`,
            timestamp: new Date(),
          },
        ]);
      }, 100);
    } else if (trimmedCmd.startsWith("/")) {
      setTimeout(() => {
        setLines((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            type: "error",
            content: `Unknown command: ${cmd}`,
            timestamp: new Date(),
          },
        ]);
      }, 100);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      executeCommand(inputValue);
      setInputValue("");
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInputValue(history[history.length - 1 - newIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInputValue(history[history.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInputValue("");
      }
    }
  };

  return (
    <div className="h-full flex flex-col bg-background text-foreground text-sm" style={{ fontFamily: "var(--font-caskaydia-cove)" }}>
      {/* Header */}
      <div className="h-12 border-b border-border/20 flex items-center justify-between px-4 bg-card/5">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-4 h-4 text-secondary" />
          <span className="font-semibold">Terminal</span>
        </div>
        <Badge
          variant="outline"
          className="text-xs border-destructive/30 text-destructive"
        >
          ROOT ACCESS
        </Badge>
      </div>

      {/* Output Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2 min-h-0">
        {allLines.map((line) => {
          const Icon = lineIcons[line.type];
          
          // Check if line contains folder structure or box drawing characters
          const hasBoxChars = /[─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬]/.test(line.content);
          const isStructureLine = /^[\s│├└─]+/.test(line.content) || 
                                  line.content.includes('├──') || 
                                  line.content.includes('└──') ||
                                  line.content.includes('│') ||
                                  hasBoxChars;

          return (
            <motion.div
              key={line.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className={cn("flex items-start gap-2", lineColors[line.type])}
            >
              {Icon && <Icon className="w-4 h-4 mt-0.5 shrink-0" />}
              {isStructureLine ? (
                <pre className="whitespace-pre font-mono text-sm m-0 p-0" style={{ fontFamily: 'inherit' }}>{line.content}</pre>
              ) : (
                <span className="break-all">{linkifyContent(line.content)}</span>
              )}
            </motion.div>
          );
        })}
        <div ref={scrollRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border/20 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-accent">root@helios</span>
          <span className="text-muted-foreground">:</span>
          <span className="text-primary">~</span>
          <span className="text-muted-foreground">$</span>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent outline-none text-foreground ml-2"
            placeholder="Enter command..."
            autoFocus
          />
        </div>
      </div>

      {/* Quick Commands */}
      <div className="px-4 pb-4 flex gap-2 flex-wrap flex-shrink-0">
        <button
          onClick={() => {
            setLines([]);
            clearTerminal();
          }}
          className="px-2 py-1 text-xs rounded bg-muted/20 hover:bg-muted/30 transition-colors"
        >
          Clear All
        </button>
        {Object.keys(commandResponses)
          .filter((cmd) => !cmd.includes(" "))
          .map((cmd) => (
            <button
              key={cmd}
              onClick={() => {
                setInputValue(cmd);
                inputRef.current?.focus();
              }}
              className="px-2 py-1 text-xs rounded bg-muted/20 hover:bg-muted/30 transition-colors"
            >
              {cmd}
            </button>
          ))}
      </div>
    </div>
  );
}
