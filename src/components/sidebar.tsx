"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutGrid,
  MessageSquare,
  Terminal,
  Layers,
  Plus,
  ChevronRight,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

const navItems: NavItem[] = [
  { id: "canvas", label: "Blueprint", icon: LayoutGrid },
  { id: "chat", label: "Chat", icon: MessageSquare, badge: "3" },
  { id: "terminal", label: "God Mode", icon: Terminal },
  { id: "multiverse", label: "Multiverse", icon: Layers },
];

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <TooltipProvider delayDuration={0}>
      <motion.div
        initial={{ width: 240 }}
        animate={{ width: collapsed ? 72 : 240 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="h-screen bg-card border-r border-border flex flex-col"
      >
        {/* Header */}
        <div className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-200 to-gray-400 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-black" />
          </div>
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="flex flex-col"
              >
                <span className="font-bold text-lg leading-tight">
                  Helios
                </span>
                <span className="text-xs text-muted-foreground">AI Studio</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Separator />

        {/* New Project Button */}
        <div className="p-3">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className={cn(
                  "w-full bg-gradient-to-r from-gray-200 to-gray-400 hover:from-gray-300 hover:to-gray-500 text-black",
                  collapsed && "p-2",
                )}
              >
                <Plus className="w-4 h-4 shrink-0" />
                <AnimatePresence mode="wait">
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: "auto" }}
                      exit={{ opacity: 0, width: 0 }}
                      className="ml-2 overflow-hidden whitespace-nowrap"
                    >
                      New Task
                    </motion.span>
                  )}
                </AnimatePresence>
              </Button>
            </TooltipTrigger>
            {collapsed && (
              <TooltipContent side="right">New Task</TooltipContent>
            )}
          </Tooltip>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onViewChange(item.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 relative group",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    )}
                  >
                    <Icon className="w-5 h-5 shrink-0" />
                    <AnimatePresence mode="wait">
                      {!collapsed && (
                        <motion.span
                          initial={{ opacity: 0, width: 0 }}
                          animate={{ opacity: 1, width: "auto" }}
                          exit={{ opacity: 0, width: 0 }}
                          className="flex-1 text-left overflow-hidden whitespace-nowrap"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </AnimatePresence>
                    {!collapsed && item.badge && (
                      <Badge
                        variant={isActive ? "secondary" : "default"}
                        className="h-5 px-1.5 text-xs"
                      >
                        {item.badge}
                      </Badge>
                    )}
                    {isActive && (
                      <motion.div
                        layoutId="activeIndicator"
                        className="absolute left-0 w-1 h-6 bg-gradient-to-b from-gray-200 to-gray-400 rounded-r-full"
                      />
                    )}
                  </button>
                </TooltipTrigger>
                {collapsed && (
                  <TooltipContent side="right">{item.label}</TooltipContent>
                )}
              </Tooltip>
            );
          })}
        </nav>

        <Separator />

        {/* Collapse Toggle */}
        <div className="p-3">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCollapsed(!collapsed)}
                className={cn(
                  "w-full justify-center text-muted-foreground hover:text-foreground",
                  !collapsed && "justify-between",
                )}
              >
                <AnimatePresence mode="wait">
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-xs"
                    >
                      Collapse
                    </motion.span>
                  )}
                </AnimatePresence>
                <ChevronRight
                  className={cn(
                    "w-4 h-4 transition-transform duration-300",
                    collapsed && "rotate-180",
                  )}
                />
              </Button>
            </TooltipTrigger>
            {collapsed && <TooltipContent side="right">Expand</TooltipContent>}
          </Tooltip>
        </div>
      </motion.div>
    </TooltipProvider>
  );
}
