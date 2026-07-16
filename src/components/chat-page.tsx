"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  Users,
  AtSign,
  ChevronRight,
  ChevronDown,
  Bot,
  User,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  useOrchestratorStore,
  type ChatMessage,
} from "@/lib/orchestrator-store";

/** Agent descriptor used for @-mentions in the comms hub. */
interface AgentRef {
  id: string;
  name: string;
}

interface FileNode {
  name: string;
  type: "file" | "folder";
  children?: FileNode[];
  assignedTo?: string;
  status?: "working" | "done" | "pending";
}


function FileTree({ nodes, depth = 0 }: { nodes: FileNode[]; depth?: number }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    src: true,
    components: true,
    api: true,
  });

  const statusColors: Record<string, string> = {
    working: "bg-amber-400",
    done: "bg-emerald-400",
    pending: "bg-gray-400",
  };

  return (
    <div className="space-y-0.5">
      {nodes.map((node) => (
        <div key={node.name}>
          <button
            onClick={() =>
              node.type === "folder" &&
              setExpanded({ ...expanded, [node.name]: !expanded[node.name] })
            }
            className={cn(
              "w-full flex items-center gap-2 px-2 py-1 rounded text-sm hover:bg-accent transition-colors",
              depth > 0 && "ml-4",
            )}
          >
            {node.type === "folder" ? (
              <>
                {expanded[node.name] ? (
                  <ChevronDown className="w-3 h-3 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-3 h-3 text-muted-foreground" />
                )}
                {expanded[node.name] ? (
                  <FolderOpen className="w-4 h-4 text-amber-400" />
                ) : (
                  <Folder className="w-4 h-4 text-amber-400" />
                )}
              </>
            ) : (
              <>
                <span className="w-3" />
                <FileCode className="w-4 h-4 text-gray-400" />
              </>
            )}
            <span className="flex-1 text-left truncate">{node.name}</span>
            {node.status && (
              <span
                className={cn(
                  "w-2 h-2 rounded-full",
                  statusColors[node.status],
                )}
              />
            )}
          </button>
          {node.type === "folder" && expanded[node.name] && node.children && (
            <FileTree nodes={node.children} depth={depth + 1} />
          )}
        </div>
      ))}
    </div>
  );
}

function MessageBubble({
  message,
  compact = false,
}: {
  message: ChatMessage;
  compact?: boolean;
}) {
  return (
    <div className={cn("flex gap-2", compact ? "gap-2" : "gap-3")}>
      <Avatar className={cn(compact ? "w-6 h-6" : "w-8 h-8", "shrink-0")}>
        <AvatarFallback
          className={cn(
            compact ? "text-[10px]" : "text-xs",
            "font-medium",
            message.isUser
              ? "bg-muted"
              : "bg-gradient-to-br from-gray-200 to-gray-400 text-black",
          )}
        >
          {message.avatar}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1 mb-0.5">
          <span
            className={cn(compact ? "text-xs" : "text-sm", "font-semibold")}
          >
            {message.author}
          </span>
          {!message.isUser && compact && (
            <Badge variant="outline" className="h-4 text-[10px] px-1">
              AI
            </Badge>
          )}
          <span className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <p
          className={cn(
            compact ? "text-xs text-muted-foreground" : "text-sm",
            "leading-relaxed",
          )}
        >
          {message.content}
        </p>
      </div>
    </div>
  );
}

export function ChatPage() {
  const {
    chatMessages,
    agentMessages,
    wrappers,
    connected,
    connect,
    sendChatMessage,
    sendEnvelope,
    projectFiles,
  } = useOrchestratorStore();

  const [userInput, setUserInput] = useState("");
  const [agentInput, setAgentInput] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const userScrollRef = useRef<HTMLDivElement>(null);
  const agentScrollRef = useRef<HTMLDivElement>(null);

  /** Auto-connect to the orchestrator when the chat page mounts. */
  const ORCHESTRATOR_URL =
    process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "ws://127.0.0.1:8788/ws";

  useEffect(() => {
    if (!connected) connect(ORCHESTRATOR_URL);
    // Don't disconnect on unmount — the WS connection is shared across views
  }, []);

  /** Derive available agents from live wrappers (excluding ui-observer). */
  const agents: AgentRef[] = Object.values(wrappers)
    .filter((w) => w.type !== "ui-observer")
    .map((w) => ({ id: w.id, name: w.meta.name }));

  useEffect(() => {
    userScrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  useEffect(() => {
    agentScrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [agentMessages]);

  /** Send user message through PM wrapper and execute ML pipeline. */
  const handleUserSend = async () => {
    if (!userInput.trim()) return;
    const text = userInput.trim();

    sendChatMessage(text);
    setUserInput("");
  };

  /** Agent @-mention input helper. */
  const handleAgentInput = (value: string) => {
    setAgentInput(value);
    setShowMentions(
      value.includes("@") && !value.includes(" ", value.lastIndexOf("@")),
    );
  };

  /** Insert an @mention into the agent input. */
  const insertMention = (agentName: string) => {
    const lastAt = agentInput.lastIndexOf("@");
    const newValue = agentInput.slice(0, lastAt) + `@${agentName} `;
    setAgentInput(newValue);
    setShowMentions(false);
  };

  /** Send a free-form message from the agent comms input. */
  const handleAgentSend = () => {
    if (!agentInput.trim()) return;
    const text = agentInput.trim();

    // Check for @mention to route to a specific wrapper
    const mentionMatch = text.match(/@(\S+)/);
    const targetAgent = mentionMatch
      ? agents.find((a) => a.name === mentionMatch[1])
      : null;

    if (targetAgent) {
      sendEnvelope({
        type: "EVENT",
        src: "ui-observer",
        dst: targetAgent.id,
        ts: Date.now(),
        payload: { kind: "CHAT_MESSAGE", text },
      });
    } else {
      // Route through PM if no specific target
      sendChatMessage(text);
    }
    setAgentInput("");
  };

  // Build file tree from flat file list
  const buildFileTree = (files: string[]): FileNode[] => {
    const root: Record<string, any> = {};
    
    files.forEach(filepath => {
      const parts = filepath.split('/');
      let current = root;
      
      parts.forEach((part, index) => {
        if (!current[part]) {
          current[part] = index === parts.length - 1 
            ? { _isFile: true, _path: filepath }
            : {};
        }
        current = current[part];
      });
    });
    
    const convertToNodes = (obj: Record<string, any>, path: string = ''): FileNode[] => {
      return Object.keys(obj).map(key => {
        const value = obj[key];
        const fullPath = path ? `${path}/${key}` : key;
        
        if (value._isFile) {
          return {
            name: key,
            type: 'file' as const,
            status: 'done' as const,
          };
        } else {
          return {
            name: key,
            type: 'folder' as const,
            children: convertToNodes(value, fullPath),
          };
        }
      });
    };
    
    return convertToNodes(root);
  };

  const fileTreeNodes = buildFileTree(projectFiles);

  return (
    <div className="h-full flex bg-background overflow-hidden">
      {/* -------- Left Panel – Main User Chat -------- */}
      <div className="flex-1 flex flex-col border-r border-border min-w-0">
        <div className="h-12 border-b border-border flex items-center px-4 flex-shrink-0">
          <User className="w-4 h-4 mr-2 text-muted-foreground" />
          <span className="font-semibold text-sm">Main Chat</span>
          <Badge variant="secondary" className="ml-2 text-xs">
            You → Helios
          </Badge>
          {connected ? (
            <span className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Live
            </span>
          ) : (
            <span className="ml-auto flex items-center gap-1.5 text-xs text-red-400">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Offline
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
          {chatMessages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm">
              <Bot className="w-8 h-8 mb-2 opacity-40" />
              <p>Tell Helios what to build…</p>
              <p className="text-xs mt-1 opacity-60">
                Your request is interpreted locally and compiled into a working site.
              </p>
            </div>
          )}

          <AnimatePresence mode="popLayout">
            {chatMessages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <MessageBubble message={message} />
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={userScrollRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border flex-shrink-0">
          <div className="flex gap-2">
            <Input
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleUserSend()}
              placeholder="Describe the website you want Helios to build..."
              className="flex-1"
            />
            <Button onClick={handleUserSend} size="icon">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* -------- Right Panel -------- */}
      <div className="w-96 flex flex-col flex-shrink-0 overflow-hidden">
        {/* Top — Folder Structure & Team Activity */}
        <div className="flex-1 border-b border-border overflow-hidden flex flex-col min-h-0">
          <div className="h-12 border-b border-border flex items-center px-4 flex-shrink-0">
            <Folder className="w-4 h-4 mr-2 text-muted-foreground" />
            <span className="font-semibold text-sm">Project Files</span>
          </div>
          <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 min-h-0">
            {fileTreeNodes.length > 0 ? (
              <FileTree nodes={fileTreeNodes} />
            ) : (
              <p className="text-xs text-muted-foreground text-center mt-8">
                No files yet. Start a project to see generated files here.
              </p>
            )}
          </div>

          <Separator />

          {/* Team Activity — derived from live wrapper statuses */}
          <div className="p-3 flex-shrink-0">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">
                Team Activity
              </span>
            </div>
            <div className="space-y-2">
              {Object.values(wrappers)
                .filter((w) => w.type !== "ui-observer")
                .map((w) => (
                  <div key={w.id} className="flex items-center gap-2 text-xs">
                    <span
                      className={cn(
                        "w-2 h-2 rounded-full",
                        w.status === "WORKING" &&
                        "bg-emerald-400 animate-pulse",
                        w.status === "THINKING" && "bg-amber-400 animate-pulse",
                        w.status === "BLOCKED" && "bg-red-400 animate-pulse",
                        w.status === "IDLE" && "bg-zinc-400",
                      )}
                    />
                    <span className="font-medium">{w.meta.name}</span>
                    <span className="text-muted-foreground capitalize">
                      {w.status.toLowerCase()}
                    </span>
                  </div>
                ))}
              {Object.keys(wrappers).length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No agents connected
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Bottom — Comms Hub (agent messages) */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="h-12 border-b border-border flex items-center px-4 flex-shrink-0">
            <Bot className="w-4 h-4 mr-2 text-muted-foreground" />
            <span className="font-semibold text-sm">Comms Hub</span>
            <Badge variant="outline" className="ml-2 text-xs">
              AI Agents
            </Badge>
          </div>

          {/* Agent Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
            {agentMessages.length === 0 && (
              <p className="text-xs text-muted-foreground text-center mt-4 opacity-60">
                Agent responses will appear here…
              </p>
            )}
            {agentMessages.map((message) => (
              <MessageBubble key={message.id} message={message} compact />
            ))}
            <div ref={agentScrollRef} />
          </div>

          {/* Agent Input with @mentions */}
          <div className="p-3 border-t border-border relative flex-shrink-0">
            {showMentions && agents.length > 0 && (
              <div className="absolute bottom-full left-3 right-3 mb-1 bg-popover border border-border rounded-lg shadow-lg p-1">
                {agents.map((agent) => (
                  <button
                    key={agent.id}
                    onClick={() => insertMention(agent.name)}
                    className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded hover:bg-accent transition-colors"
                  >
                    <AtSign className="w-3 h-3 text-muted-foreground" />
                    {agent.name}
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <Input
                value={agentInput}
                onChange={(e) => handleAgentInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAgentSend()}
                placeholder="Use @ to ping agents..."
                className="flex-1 text-xs h-8"
              />
              <Button
                size="sm"
                className="h-8 px-2"
                onClick={handleAgentSend}
              >
                <Send className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
