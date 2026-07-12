"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { GlassCard, type UniverseData } from "./glass-card";

interface CardStreamProps {
  /** Array of universe data */
  universes: UniverseData[];
  /** Callback when a card is selected */
  onSelectCard: (universe: UniverseData, index: number) => void;
  /** Callback when hover state changes */
  onHoverChange?: (universe: UniverseData | null, index: number | null) => void;
  /** Index of the active/current workspace */
  activeIndex?: number;
  /** Card expansion progress from 0 (all hidden) to 1 (fully expanded) */
  cardExpandProgress?: number;
}

// Stream configuration for diagonal cycling cards
const STREAM_CONFIG = {
  /** Angle of the diagonal line (radians) */
  angle: Math.PI / 5,
  /** Spacing between cards along the stream - increased to prevent text overlap */
  spacing: 3.2,
  /** Rotation of cards to face camera better */
  cardRotationY: -Math.PI / 40,
  /** Slight tilt for premium feel */
  cardRotationX: 0.12,
  /** Scroll sensitivity */
  scrollSensitivity: 0.004,
  /** Damping for smooth scroll */
  damping: 0.92,
  /** Offset to position stream */
  originOffset: { x: 0, y: 0, z: 0 },
};

/**
 * CardStream - Cards move in a circular diagonal stream
 *
 * Implements infinite scrolling with cards cycling like a circular linked list.
 * Camera stays fixed, cards move through the scene.
 */
export function CardStream({
  universes,
  onSelectCard,
  onHoverChange,
  activeIndex = 0,
  cardExpandProgress = 0,
}: CardStreamProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const groupRef = useRef<THREE.Group>(null);
  const { gl } = useThree();

  // Scrolling only enabled after card expansion completes
  const canScroll = cardExpandProgress >= 1;

  // Duplicate universes to ensure at least 10 cards are always rendered
  const minCards = 10;
  const repetitions =
    universes.length === 0
      ? 0
      : Math.max(2, Math.ceil(minCards / universes.length));
  const extendedUniverses = Array.from({ length: repetitions }, (_, repIndex) =>
    universes.map((universe, idx) => ({
      ...universe,
      // Make each duplicate unique with a suffix
      id: `${universe.id}-rep${repIndex}`,
      originalIndex: idx,
      repetitionIndex: repIndex,
    })),
  ).flat();

  // Scroll state - accumulates infinitely, wraps for position calculation
  const scrollOffset = useRef(0);
  const scrollVelocity = useRef(0);

  // Handle hover change and notify parent
  const handleHoverChange = useCallback(
    (index: number | null) => {
      setHoveredIndex(index);
      if (onHoverChange) {
        if (index !== null) {
          const extUniverse = extendedUniverses[index];
          const originalUniverse = universes[extUniverse.originalIndex];
          onHoverChange(originalUniverse, extUniverse.originalIndex);
        } else {
          onHoverChange(null, null);
        }
      }
    },
    [onHoverChange, extendedUniverses, universes],
  );

  // Handle wheel events for scrolling
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      if (!canScroll) return; // Only scroll after zoom out
      e.preventDefault();
      scrollVelocity.current += e.deltaY * STREAM_CONFIG.scrollSensitivity;
    },
    [canScroll],
  );

  // Register wheel listener on mount
  useEffect(() => {
    const canvas = gl.domElement;
    canvas.addEventListener("wheel", handleWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", handleWheel);
  }, [gl, handleWheel]);

  // Reset scroll and hover when universes change
  useEffect(() => {
    scrollOffset.current = 0;
    scrollVelocity.current = 0;
    setHoveredIndex(null);
  }, [universes.length]);

  // Easing for smooth animation
  const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
  // Custom easing: starts at 0, ends at 1, with slight overshoot
  const easeOutBack = (t: number) => {
    if (t <= 0) return 0; // Ensure we start at exactly 0
    if (t >= 1) return 1; // Ensure we end at exactly 1
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  };

  // Find the index of the active card in extendedUniverses (first occurrence)
  const activeCardIndex = extendedUniverses.findIndex(
    (u) => u.originalIndex === activeIndex && u.repetitionIndex === 0,
  );

  // Animate cards each frame
  useFrame(() => {
    // Apply velocity with damping (only when can scroll)
    if (canScroll) {
      scrollOffset.current += scrollVelocity.current;
      scrollVelocity.current *= STREAM_CONFIG.damping;

      // Stop tiny movements
      if (Math.abs(scrollVelocity.current) < 0.0001) {
        scrollVelocity.current = 0;
      }
    }

    // Update each card's position
    if (groupRef.current) {
      const children = groupRef.current.children as THREE.Group[];
      const numCards = extendedUniverses.length;
      const { angle, spacing } = STREAM_CONFIG;

      // Eased expansion progress for smooth card pop-out animation
      const easedProgress = easeOutBack(cardExpandProgress);

      children.forEach((child, index) => {
        const extUniverse = extendedUniverses[index];
        const isActiveCard =
          extUniverse.originalIndex === activeIndex &&
          extUniverse.repetitionIndex === 0;

        // Calculate position relative to active card (active card = center = 0)
        let relativeIndex = index - activeCardIndex;

        // Wrap around for infinite scroll effect
        const halfCards = numCards / 2;
        if (relativeIndex > halfCards) relativeIndex -= numCards;
        if (relativeIndex < -halfCards) relativeIndex += numCards;

        // Apply scroll offset
        let streamPos = relativeIndex * spacing - scrollOffset.current;

        // Wrap stream position for infinite scrolling
        const totalLength = numCards * spacing;
        streamPos =
          (((streamPos % totalLength) + totalLength + totalLength / 2) %
            totalLength) -
          totalLength / 2;

        // Final position in the diagonal stream
        const finalX = Math.cos(angle) * streamPos;
        const finalZ = Math.sin(angle) * streamPos;
        const finalY = streamPos * -0.02; // Subtle Y offset for depth

        if (isActiveCard) {
          // Active card: always visible, starts at center, moves to stream position
          const x = finalX * easedProgress;
          const y = finalY * easedProgress;
          const z = finalZ * easedProgress;
          child.position.set(x, y, z);
          child.userData.streamOpacity = 1;
          child.visible = true;
        } else {
          // Other cards: hidden until expansion starts, then expand from center
          if (cardExpandProgress <= 0) {
            // Before expansion: hide other cards completely
            child.visible = false;
            child.position.set(0, 0, 0);
            child.userData.streamOpacity = 0;
          } else {
            // During/after expansion: show and animate to final positions
            child.visible = true;
            const x = finalX * easedProgress;
            const y = finalY * easedProgress;
            const z = finalZ * easedProgress;
            child.position.set(x, y, z);

            // Fade in as they expand
            const opacity = easeOutCubic(cardExpandProgress);
            child.userData.streamOpacity = opacity;
          }
        }
      });
    }
  });

  return (
    <group
      ref={groupRef}
      position={[
        STREAM_CONFIG.originOffset.x,
        STREAM_CONFIG.originOffset.y,
        STREAM_CONFIG.originOffset.z,
      ]}
    >
      {extendedUniverses.map((universe, index) => (
        <GlassCard
          key={universe.id}
          universe={universe}
          position={[0, 0, 0]}
          rotation={[
            STREAM_CONFIG.cardRotationX,
            STREAM_CONFIG.cardRotationY,
            0,
          ]}
          isHovered={hoveredIndex === index}
          isActive={
            universe.originalIndex === activeIndex &&
            universe.repetitionIndex === 0
          }
          onPointerEnter={() => handleHoverChange(index)}
          onPointerLeave={() => handleHoverChange(null)}
          onClick={() =>
            onSelectCard(
              universes[universe.originalIndex],
              universe.originalIndex,
            )
          }
          index={universe.originalIndex}
        />
      ))}
    </group>
  );
}

export default CardStream;
