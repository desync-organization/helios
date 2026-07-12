"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Hash,
  Lock,
  MoreHorizontal,
  Code2,
  FileJson,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useOrchestratorStore } from "@/lib/orchestrator-store";

type ChannelType = "general" | "engineering" | "frontend" | "ops";
type MessageType = "text" | "code" | "json" | "mermaid";

interface Message {
  id: string;
  channel: ChannelType;
  author: string;
  avatar: string;
  content: string;
  type: MessageType;
  timestamp: Date;
  isAgent: boolean;
}

interface Channel {
  id: ChannelType;
  name: string;
  icon: LucideIcon;
  unread: number;
  locked: boolean;
}

const channels: Channel[] = [
  { id: "general", name: "general", icon: Hash, unread: 0, locked: false },
  {
    id: "engineering",
    name: "engineering-core",
    icon: Code2,
    unread: 3,
    locked: false,
  },
  {
    id: "frontend",
    name: "frontend-design",
    icon: Workflow,
    unread: 1,
    locked: false,
  },
  { id: "ops", name: "ops-security", icon: Lock, unread: 0, locked: true },
];

// Removed initialMessages

function MessageContent({ message }: { message: Message }) {
  if (message.type === "code") {
    return (
      <pre className="mt-2 p-3 bg-muted/50 rounded-lg overflow-x-auto text-sm font-mono">
        <code>{message.content.replace(/```[a-z]*\n?/g, "")}</code>
      </pre>
    );
  }

  return <p className="text-sm leading-relaxed">{message.content}</p>;
}

export function CommunicationHub() {
  const [activeChannel, setActiveChannel] = useState<ChannelType>("general");
  const [inputValue, setInputValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { chatMessages, agentMessages, sendChatMessage, connected, connect } = useOrchestratorStore();

  // Auto-connect if needed
  useEffect(() => {
    if (!connected) {
      const URL = process.env.NEXT_PUBLIC_ML_SERVICE_URL ?? "ws://localhost:9100";
      connect(URL);
    }
  }, [connected, connect]);

  // Transform store messages to local format
  const messages: Message[] = [
    // General channel: Chat messages
    ...chatMessages.map(m => ({
      id: m.id,
      channel: "general" as ChannelType,
      author: m.author,
      avatar: m.avatar,
      content: m.content,
      type: "text" as MessageType, // simplistic for now
      timestamp: new Date(m.timestamp),
      isAgent: !m.isUser,
    })),
    // Engineering channel: Agent messages
    ...agentMessages.map(m => ({
      id: m.id,
      channel: "engineering" as ChannelType,
      author: m.author,
      avatar: m.avatar,
      content: m.content,
      type: "text" as MessageType,
      timestamp: new Date(m.timestamp),
      isAgent: true,
    }))
  ].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, activeChannel]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    if (activeChannel === "general") {
      const text = inputValue.trim();
      sendChatMessage(text);
    } else {
      // For now, only general is interactive for user
      console.warn("Sending in non-general channels not yet implemented without @mentions");
    }
    setInputValue("");
  };

  const filteredMessages = messages.filter((m) => m.channel === activeChannel);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Channel Sidebar */}
      <div className="w-64 border-r border-border bg-card/50 flex-shrink-0">
        <div className="p-4">
          <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
            Channels
          </h2>
        </div>
        <nav className="px-2 space-y-1">
          {channels.map((channel) => {
            const Icon = channel.icon;
            const isActive = activeChannel === channel.id;

            return (
              <button
                key={channel.id}
                onClick={() => setActiveChannel(channel.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="flex-1 text-left">{channel.name}</span>
                {channel.locked && <Lock className="w-3 h-3" />}
                {channel.unread > 0 && (
                  <Badge variant="default" className="h-5 px-1.5 text-xs">
                    {channel.unread}
                  </Badge>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <div className="h-14 border-b border-border flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-muted-foreground" />
            <span className="font-semibold">
              {channels.find((c) => c.id === activeChannel)?.name}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              Spectator Mode
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreHorizontal className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>Hijack Channel</DropdownMenuItem>
                <DropdownMenuItem>Mute Notifications</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
          <AnimatePresence mode="popLayout">
            {filteredMessages.map((message, index) => {
              const showAvatar =
                index === 0 ||
                filteredMessages[index - 1].author !== message.author;

              return (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={cn("flex gap-3", !showAvatar && "pl-[52px]")}
                >
                  {showAvatar && (
                    <Avatar className="w-10 h-10 shrink-0">
                      <AvatarFallback
                        className={cn(
                          "text-xs font-medium",
                          message.isAgent
                            ? "bg-gradient-to-br from-gray-200 to-gray-400 text-black"
                            : "bg-muted",
                        )}
                      >
                        {message.avatar}
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div className="flex-1 min-w-0">
                    {showAvatar && (
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm">
                          {message.author}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        {message.isAgent && (
                          <Badge variant="outline" className="h-4 text-[10px]">
                            AI
                          </Badge>
                        )}
                      </div>
                    )}
                    <MessageContent message={message} />
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
          <div ref={scrollRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border flex-shrink-0">
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder={
                activeChannel === "general"
                  ? "Message #general..."
                  : `Message #${activeChannel}...`
              }
              className="flex-1"
            />
            <Button onClick={handleSend} size="icon">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
