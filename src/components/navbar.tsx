"use client";

import { useRef } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  type MotionValue,
} from "framer-motion";
import {
  LayoutGrid,
  MessageSquare,
  Terminal,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DockItem {
  id: string;
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
}

interface NavbarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onSettingsClick?: () => void;
}

/**
 * Single dock icon with macOS-style magnification on hover.
 * Reads the shared mouseX motion value to compute distance-based scale.
 */
function DockIcon({
  item,
  mouseX,
  isActive,
}: {
  item: DockItem;
  mouseX: MotionValue<number>;
  isActive: boolean;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const Icon = item.icon;

  const distance = useTransform(mouseX, (val: number) => {
    const bounds = ref.current?.getBoundingClientRect() ?? { x: 0, width: 0 };
    return val - bounds.x - bounds.width / 2;
  });

  const widthSync = useTransform(distance, [-120, 0, 120], [32, 48, 32]);
  const width = useSpring(widthSync, {
    mass: 0.1,
    stiffness: 200,
    damping: 14,
  });

  return (
    <motion.button
      ref={ref}
      style={{ width, height: width }}
      onClick={item.onClick}
      className={cn(
        "relative flex items-center justify-center rounded-lg transition-colors",
        "bg-white/10 backdrop-blur-sm hover:bg-white/20",
        isActive && "bg-white/25 ring-1 ring-white/30",
      )}
      whileTap={{ scale: 0.85 }}
      aria-label={item.label}
    >
      <Icon className="w-[40%] h-[40%] text-foreground" />

      {/* Active dot indicator */}
      {isActive && (
        <motion.div
          layoutId="dock-active-dot"
          className="absolute -bottom-1.5 w-1 h-1 rounded-full bg-foreground"
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
        />
      )}

      {/* Tooltip on hover */}
      <span className="pointer-events-none absolute -top-9 rounded-md bg-card/90 border border-border px-2 py-1 text-xs text-foreground opacity-0 transition-opacity group-hover:opacity-100 whitespace-nowrap backdrop-blur-md">
        {item.label}
      </span>
    </motion.button>
  );
}

/**
 * Floating macOS-style dock navbar.
 * Pinned to the bottom-center of the viewport, with magnification on hover.
 */
export function Navbar({
  activeView,
  onViewChange,
  onSettingsClick,
}: NavbarProps) {
  const mouseX = useMotionValue(Infinity);

  const items: DockItem[] = [
    {
      id: "canvas",
      label: "Blueprint Canvas",
      icon: LayoutGrid,
      onClick: () => onViewChange("canvas"),
    },
    {
      id: "chat",
      label: "Communication Hub",
      icon: MessageSquare,
      onClick: () => onViewChange("chat"),
    },
    {
      id: "terminal",
      label: "Terminal",
      icon: Terminal,
      onClick: () => onViewChange("terminal"),
    },

    {
      id: "settings",
      label: "Settings",
      icon: Settings,
      onClick: onSettingsClick,
    },
  ];

  return (
    <motion.div
      onMouseMove={(e) => mouseX.set(e.pageX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className={cn(
        "fixed bottom-3 left-1/2 z-50 flex items-center gap-1 px-2 py-1",
        "rounded-xl border border-white/10 bg-black/40 backdrop-blur-xl shadow-2xl",
        "-translate-x-1/2",
      )}
    >
      {items.map((item) => (
        <div key={item.id} className="group flex items-center">
          {item.id === "settings" && (
            <div className="mr-1 h-5 w-px bg-white/15" />
          )}
          <div className="group flex items-center">
            <DockIcon
              item={item}
              mouseX={mouseX}
              isActive={item.id === activeView}
            />
          </div>
        </div>
      ))}
    </motion.div >
  );
}
