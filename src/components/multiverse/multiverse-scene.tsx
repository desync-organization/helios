"use client";

import { Suspense, useRef, useState, useCallback, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, PerspectiveCamera, Preload } from "@react-three/drei";
import * as THREE from "three";
import { CardStream } from "./card-stream";
import type { UniverseData } from "./glass-card";
import { useGitStore, type GitBranch } from "@/lib/git-store";
import { MultiverseControls } from "./multiverse-controls";

// Camera positions
// Fullscreen: Camera looking straight at a card that fills the viewport
const CAMERA_FULLSCREEN = new THREE.Vector3(0, 0, 3.5);
// Zoomed out: Elevated view showing the diagonal card stream
const CAMERA_ZOOMED_OUT = new THREE.Vector3(0, 2.5, 9);

// Animation timing (in seconds)
const INITIAL_PAUSE = 1.0; // Show reference card alone
const CAMERA_ZOOM_DURATION = 1.0; // Camera zooms out
const CARD_EXPAND_DURATION = 0.8; // Cards expand from reference
const TOTAL_ANIMATION = CAMERA_ZOOM_DURATION + CARD_EXPAND_DURATION;

/**
 * Convert git branches to universe data for the 3D scene.
 * Arranges branches in alternating pattern: main, branch, main, branch, etc.
 */
function branchesToUniverses(branches: GitBranch[]): UniverseData[] {
  const colors = [
    "#e693bc",
    "#fa0f83",
    "#911150",
    "#ff3366",
    "#d876a7",
    "#b84581",
    "#7a0d42",
    "#ff5a9f",
    "#c05898",
    "#a03370",
  ];

  // Find the active (main) branch
  const activeBranch = branches.find((b) => b.isActive);
  const otherBranches = branches.filter((b) => !b.isActive);

  // If no branches or only one branch, return as-is
  if (branches.length <= 1 || !activeBranch) {
    return branches.map((branch, index) => ({
      id: branch.id,
      name: branch.name,
      description: branch.isActive ? "Active branch" : "Branch",
      branchName: branch.name,
      color: colors[index % colors.length],
    }));
  }

  // Create alternating pattern: main, other, main, other, etc.
  const alternatingBranches: GitBranch[] = [];
  for (let i = 0; i < Math.max(otherBranches.length, 1); i++) {
    // Add main branch
    alternatingBranches.push(activeBranch);
    // Add other branch if available
    if (i < otherBranches.length) {
      alternatingBranches.push(otherBranches[i]);
    }
  }
  // Add one more main at the end if we have other branches
  if (otherBranches.length > 0) {
    alternatingBranches.push(activeBranch);
  }

  return alternatingBranches.map((branch, index) => ({
    id: `${branch.id}-${index}`, // Make each instance unique
    name: branch.name,
    description: branch.isActive ? "Active branch" : "Branch",
    branchName: branch.name,
    color: colors[index % colors.length],
  }));
}

/**
 * Camera Rig - Starts fullscreen on active card, zooms out to overview
 *
 * Animation flow:
 * 1. Start at CAMERA_FULLSCREEN looking at origin (0,0,0)
 * 2. Active card is centered at origin, other cards hidden
 * 3. Camera zooms out first (cameraProgress 0->1)
 * 4. Then cards expand from reference card (handled by CardStream)
 */
function CameraRig({
  onDive,
  diveTarget,
  cameraProgress,
}: {
  onDive: () => void;
  diveTarget: THREE.Vector3 | null;
  cameraProgress: number; // 0 = fullscreen, 1 = zoomed out
}) {
  const cameraRef = useRef<THREE.PerspectiveCamera>(null);
  const isDiving = useRef(false);
  const diveProgressRef = useRef(0);
  const originalPosition = useRef(new THREE.Vector3());

  useFrame((_, delta) => {
    if (!cameraRef.current) return;

    // Handle dive animation (clicking a card to select it)
    if (diveTarget && !isDiving.current) {
      isDiving.current = true;
      diveProgressRef.current = 0;
      originalPosition.current.copy(cameraRef.current.position);
    }

    if (isDiving.current && diveTarget) {
      diveProgressRef.current += delta * 2.5;

      if (diveProgressRef.current >= 1) {
        onDive();
        isDiving.current = false;
        diveProgressRef.current = 0;
        return;
      }

      const t = easeInOutCubic(diveProgressRef.current);
      cameraRef.current.position.lerpVectors(
        originalPosition.current,
        diveTarget.clone().add(new THREE.Vector3(0, 0, 1.5)),
        t,
      );
      cameraRef.current.lookAt(diveTarget);
      return;
    }

    // Normal camera position based on camera progress
    const t = easeOutCubic(cameraProgress);
    cameraRef.current.position.lerpVectors(
      CAMERA_FULLSCREEN,
      CAMERA_ZOOMED_OUT,
      t,
    );
    cameraRef.current.lookAt(0, 0, 0);
  });

  return (
    <PerspectiveCamera
      ref={cameraRef}
      makeDefault
      position={[CAMERA_FULLSCREEN.x, CAMERA_FULLSCREEN.y, CAMERA_FULLSCREEN.z]}
      fov={50}
      near={0.1}
      far={100}
    />
  );
}

// Easing: smooth deceleration
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

// Easing: smooth in and out
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/**
 * Scene Content - All 3D elements
 */
function SceneContent({
  universes,
  activeIndex,
  onSelectUniverse,
  onHoverChange,
  cameraProgress,
  cardExpandProgress,
  canInteract,
}: {
  universes: UniverseData[];
  activeIndex: number;
  onSelectUniverse: (universe: UniverseData, index: number) => void;
  onHoverChange?: (universe: UniverseData | null, index: number | null) => void;
  cameraProgress: number;
  cardExpandProgress: number;
  canInteract: boolean;
}) {
  const [diveTarget, setDiveTarget] = useState<THREE.Vector3 | null>(null);
  const selectedRef = useRef<{ universe: UniverseData; index: number } | null>(
    null,
  );

  const handleSelectCard = useCallback(
    (universe: UniverseData, index: number) => {
      if (!canInteract) return;
      selectedRef.current = { universe, index };
      setDiveTarget(new THREE.Vector3(0, 0, 0));
    },
    [canInteract],
  );

  const handleDiveComplete = useCallback(() => {
    if (selectedRef.current) {
      onSelectUniverse(selectedRef.current.universe, selectedRef.current.index);
    }
    setDiveTarget(null);
    selectedRef.current = null;
  }, [onSelectUniverse]);

  return (
    <>
      {/* Camera */}
      <CameraRig
        onDive={handleDiveComplete}
        diveTarget={diveTarget}
        cameraProgress={cameraProgress}
      />

      {/* Environment lighting for glass reflections */}
      <Environment preset="city" />

      {/* Additional lights */}
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[10, 10, 5]}
        intensity={1}
        castShadow
        shadow-mapSize={[2048, 2048]}
      />
      <pointLight position={[-5, 5, -5]} intensity={0.5} color="#fa0f83" />
      <pointLight position={[5, 3, 5]} intensity={0.3} color="#e693bc" />

      {/* Card Stream */}
      <CardStream
        key={`card-stream-${universes.length}`}
        universes={universes}
        onSelectCard={handleSelectCard}
        onHoverChange={onHoverChange}
        activeIndex={activeIndex}
        cardExpandProgress={cardExpandProgress}
      />
    </>
  );
}

/**
 * Loading fallback
 */
function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#333" wireframe />
    </mesh>
  );
}

/**
 * Props for MultiverseScene
 */
export interface MultiverseSceneProps {
  /** Whether the scene is visible */
  isOpen: boolean;
  /** Callback to close the scene */
  onClose: () => void;
  /** Callback when a universe is selected */
  onSelectUniverse: (universe: UniverseData, index: number) => void;
  /** Optional className */
  className?: string;
}

/**
 * MultiverseScene - The main 3D scene component
 *
 * Renders a React Three Fiber canvas with the diagonal archive of glass cards.
 */
export function MultiverseScene({
  isOpen,
  onClose,
  onSelectUniverse,
  className,
}: MultiverseSceneProps) {
  const { branches, activeBranch, fetchBranches, checkoutBranch } = useGitStore();
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);

  // Animation progress: 0-1 for camera zoom, 0-1 for card expansion (separate)
  const [cameraProgress, setCameraProgress] = useState(0);
  const [cardExpandProgress, setCardExpandProgress] = useState(0);
  const [showUI, setShowUI] = useState(false);
  const [canInteract, setCanInteract] = useState(false);
  const animationRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  // Convert branches to universes with alternating pattern
  const universes = branchesToUniverses(branches);
  // In alternating pattern, active branch is always first (index 0) or middle
  const activeIndex = 0;

  // Fetch branches on mount
  useEffect(() => {
    if (isOpen) {
      fetchBranches();
    }
  }, [isOpen, fetchBranches]);

  // Handle branch selection from cards
  const handleUniverseSelect = useCallback(
    async (universe: UniverseData, index: number) => {
      onSelectUniverse(universe, index);
      // Checkout the branch
      await checkoutBranch(universe.branchName || universe.name);
      // Refresh branches to update active state
      await fetchBranches();
    },
    [onSelectUniverse, checkoutBranch, fetchBranches],
  );

  // Handle operation complete (refresh branches)
  const handleOperationComplete = useCallback(() => {
    fetchBranches();
  }, [fetchBranches]);

  // Handle card hover to update selected branch for controls
  const handleHoverChange = useCallback(
    (universe: UniverseData | null, index: number | null) => {
      if (universe) {
        setSelectedBranch(universe.branchName || universe.name);
      } else {
        setSelectedBranch(null);
      }
    },
    [],
  );

  // Two-phase animation:
  // Phase 1: Camera zooms out (cameraProgress 0->1)
  // Phase 2: Cards expand from reference (cardExpandProgress 0->1)
  useEffect(() => {
    if (!isOpen) {
      // Reset when closed
      setCameraProgress(0);
      setCardExpandProgress(0);
      setShowUI(false);
      setCanInteract(false);
      startTimeRef.current = null;
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    // Start animation after initial pause (1 second showing reference card)
    const delayTimer = setTimeout(() => {
      const animate = (timestamp: number) => {
        if (!startTimeRef.current) {
          startTimeRef.current = timestamp;
        }

        const elapsed = (timestamp - startTimeRef.current) / 1000; // in seconds

        // Phase 1: Camera zoom (0 to CAMERA_ZOOM_DURATION)
        const camProgress = Math.min(elapsed / CAMERA_ZOOM_DURATION, 1);
        setCameraProgress(camProgress);

        // Phase 2: Card expansion (starts after camera zoom completes)
        if (elapsed > CAMERA_ZOOM_DURATION) {
          const cardElapsed = elapsed - CAMERA_ZOOM_DURATION;
          const cardProgress = Math.min(cardElapsed / CARD_EXPAND_DURATION, 1);
          setCardExpandProgress(cardProgress);
        }

        if (elapsed < TOTAL_ANIMATION) {
          animationRef.current = requestAnimationFrame(animate);
        } else {
          // Animation complete
          setCameraProgress(1);
          setCardExpandProgress(1);
          setShowUI(true);
          setCanInteract(true);
          animationRef.current = null;
        }
      };

      animationRef.current = requestAnimationFrame(animate);
    }, INITIAL_PAUSE * 1000);

    return () => {
      clearTimeout(delayTimer);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className={`relative w-full h-full bg-transparent ${className || ""}`}
      style={{ touchAction: "none" }}
    >
      {/* Multiverse Controls */}
      {showUI && (
        <MultiverseControls
          selectedBranch={selectedBranch}
          onOperationComplete={handleOperationComplete}
        />
      )}

      {/* Close button - hidden when used as a regular view */}
      {showUI && onClose && (
        <button
          onClick={onClose}
          className="absolute top-6 right-6 z-10 w-10 h-10 rounded-xl bg-primary/5 hover:bg-primary/10 border border-primary/10 flex items-center justify-center transition-colors animate-in fade-in duration-300"
        >
          <svg
            className="w-5 h-5 text-foreground/60"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}

      {/* R3F Canvas */}
      <Canvas
        shadows
        dpr={[1, 2]}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
        style={{ background: "transparent" }}
      >
        <Suspense fallback={<LoadingFallback />}>
          <SceneContent
            universes={universes}
            activeIndex={activeIndex >= 0 ? activeIndex : 0}
            onSelectUniverse={handleUniverseSelect}
            onHoverChange={handleHoverChange}
            cameraProgress={cameraProgress}
            cardExpandProgress={cardExpandProgress}
            canInteract={canInteract}
          />
          <Preload all />
        </Suspense>
      </Canvas>

      {/* Info overlay when no branches */}
      {showUI && branches.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-background/80 backdrop-blur-sm rounded-lg p-6 border border-border">
            <p className="text-muted-foreground text-center">
              No branches found. Click the + button to create one.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default MultiverseScene;
