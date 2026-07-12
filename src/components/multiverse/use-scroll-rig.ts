"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import { useThree, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface ScrollRigState {
  /** Current scroll position (0 = start, 1 = end) */
  progress: number;
  /** Target scroll position (for smooth interpolation) */
  target: number;
  /** Scroll velocity */
  velocity: number;
}

interface UseScrollRigOptions {
  /** Damping factor for smooth scrolling (0-1, lower = smoother) */
  damping?: number;
  /** Scroll sensitivity multiplier */
  sensitivity?: number;
  /** Whether scrolling is enabled */
  enabled?: boolean;
}

/**
 * Custom hook to bind mouse wheel to camera Z-position along a diagonal rail.
 * Uses lerp for smooth 60fps animation without re-renders.
 */
export function useScrollRig(options: UseScrollRigOptions = {}) {
  const { damping = 0.08, sensitivity = 0.0015, enabled = true } = options;
  
  const state = useRef<ScrollRigState>({
    progress: 0.5, // Start in middle
    target: 0.5,
    velocity: 0,
  });

  // Handle wheel events
  useEffect(() => {
    if (!enabled) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      
      const delta = e.deltaY * sensitivity;
      state.current.target = Math.max(0, Math.min(1, state.current.target + delta));
      state.current.velocity = delta;
    };

    window.addEventListener("wheel", handleWheel, { passive: false });
    return () => window.removeEventListener("wheel", handleWheel);
  }, [enabled, sensitivity]);

  // Smooth interpolation every frame
  useFrame(() => {
    if (!enabled) return;
    
    const s = state.current;
    
    // Lerp towards target
    s.progress += (s.target - s.progress) * damping;
    
    // Decay velocity
    s.velocity *= 0.9;
  });

  return state;
}

/**
 * Hook to get the current scroll progress value
 */
export function useScrollProgress(scrollRef: React.MutableRefObject<ScrollRigState>) {
  const [progress, setProgress] = useState(0.5);
  
  useFrame(() => {
    // Only update state when there's meaningful change (performance)
    const newProgress = scrollRef.current.progress;
    if (Math.abs(newProgress - progress) > 0.001) {
      setProgress(newProgress);
    }
  });
  
  return progress;
}

/**
 * Positions along the diagonal stream based on scroll progress
 */
export function getStreamPosition(
  progress: number,
  streamLength: number = 20,
  angle: number = Math.PI / 4 // 45 degree diagonal
): THREE.Vector3 {
  // Map progress (0-1) to position along diagonal line
  const t = (progress - 0.5) * streamLength;
  
  return new THREE.Vector3(
    Math.cos(angle) * t * 0.8,  // X: diagonal offset
    0,                           // Y: ground level for camera
    Math.sin(angle) * t         // Z: depth into scene
  );
}
