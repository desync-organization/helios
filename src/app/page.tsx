"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import dynamic from "next/dynamic";
import { Navbar } from "@/components/navbar";
import { BlueprintCanvas } from "@/components/blueprint-canvas";
import { SettingsDialog } from "@/components/settings-dialog";

type ViewType = "canvas" | "chat" | "terminal" | "workstation" | "cost" | "multiverse";
type StandardViewType = Exclude<ViewType, "multiverse">;

const ChatPage = dynamic(() =>
  import("@/components/chat-page").then((module) => module.ChatPage),
);
const GodModeTerminal = dynamic(() =>
  import("@/components/god-mode-terminal").then((module) => module.GodModeTerminal),
);
const Workstation = dynamic(() =>
  import("@/components/workstation").then((module) => module.Workstation),
);
const CostDashboard = dynamic(() =>
  import("@/components/cost-dashboard").then((module) => module.CostDashboard),
);
const MultiverseScene = dynamic(() =>
  import("@/components/multiverse").then((module) => module.MultiverseScene),
);

const viewComponents: Record<StandardViewType, React.ComponentType> = {
  canvas: BlueprintCanvas,
  chat: ChatPage,
  terminal: GodModeTerminal,
  workstation: Workstation,
  cost: CostDashboard,
};

export default function Home() {
  const [activeView, setActiveView] = useState<ViewType>("canvas");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const ActiveComponent = activeView === "multiverse"
    ? null
    : viewComponents[activeView];

  /**
   * Handle view changes from navbar
   */
  const handleViewChange = (view: string) => {
    setActiveView(view as ViewType);
  };

  return (
    <div className="h-screen w-full bg-background overflow-hidden">
      <Navbar
        activeView={activeView}
        onViewChange={handleViewChange}
        onSettingsClick={() => setSettingsOpen(true)}
      />
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      {/* Main Workspace Area — pb keeps content above the floating dock */}
      <div className="relative h-full w-full overflow-hidden pb-[68px]">
        {/* The GPU-heavy multiverse is mounted only while it is visible. */}
        {activeView === "multiverse" && (
          <div
            className="absolute inset-0 w-full h-full"
            style={{ zIndex: 10 }}
          >
            <MultiverseScene
              isOpen={true}
              onClose={() => {}}
              onSelectUniverse={(universe, index) => {
                console.log("Selected universe:", universe, "at index:", index);
                // Switch to canvas view after selection
                setTimeout(() => setActiveView("canvas"), 100);
              }}
            />
          </div>
        )}

        {/* Other views with transitions */}
        {activeView !== "multiverse" && ActiveComponent && (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              className="relative h-full w-full"
              style={{ zIndex: 20 }}
            >
              <ActiveComponent />
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
