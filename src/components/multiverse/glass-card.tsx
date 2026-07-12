"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import { Text, MeshTransmissionMaterial, RoundedBox } from "@react-three/drei";
import * as THREE from "three";

/**
 * Universe data for a glass card
 */
export interface UniverseData {
  id: string;
  name: string;
  description?: string;
  branchName?: string;
  color?: string;
}

interface GlassCardProps {
  /** Universe data */
  universe: UniverseData;
  /** Position in 3D space */
  position: [number, number, number];
  /** Rotation (euler angles) */
  rotation?: [number, number, number];
  /** Whether this card is currently hovered */
  isHovered: boolean;
  /** Whether this card is the active/current workspace */
  isActive?: boolean;
  /** Callback when pointer enters */
  onPointerEnter: () => void;
  /** Callback when pointer leaves */
  onPointerLeave: () => void;
  /** Callback when clicked */
  onClick: () => void;
  /** Index for stagger animations */
  index: number;
}

// Card dimensions - PAPER THIN
const CARD_WIDTH = 3.2;
const CARD_HEIGHT = 2.2;
const CARD_DEPTH = 0.008; // Paper thin!
const CARD_RADIUS = 0.04;

/**
 * GlassCard - A paper-thin frosted glass card component
 *
 * Uses MeshTransmissionMaterial for realistic glass rendering
 * with hover levitation and click interactions.
 */
export function GlassCard({
  universe,
  position,
  rotation = [0, 0, 0],
  isHovered,
  isActive = false,
  onPointerEnter,
  onPointerLeave,
  onClick,
  index,
}: GlassCardProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshPhysicalMaterial>(null);

  // Animated values
  const animatedY = useRef(0);
  const animatedScale = useRef(1);
  const currentOpacity = useRef(1);

  // Target values based on hover state
  const targetY = isHovered ? 0.3 : 0;
  const targetScale = isHovered ? 1.08 : 1;

  // Smooth animation each frame
  useFrame((_, delta) => {
    if (!groupRef.current) return;

    const lerpFactor = 1 - Math.pow(0.001, delta);

    // Read opacity from parent's userData (set by CardStream)
    const parentOpacity = groupRef.current.userData.streamOpacity ?? 1;
    currentOpacity.current +=
      (parentOpacity - currentOpacity.current) * lerpFactor * 10;

    // Lerp Y position (levitate on hover)
    animatedY.current += (targetY - animatedY.current) * lerpFactor * 10;

    // Lerp scale
    animatedScale.current +=
      (targetScale - animatedScale.current) * lerpFactor * 10;
    groupRef.current.scale.setScalar(animatedScale.current);

    // Apply Y offset for hover levitation
    groupRef.current.position.y +=
      animatedY.current - (groupRef.current.userData.lastY ?? 0);
    groupRef.current.userData.lastY = animatedY.current;

    // Update material opacity
    if (materialRef.current) {
      materialRef.current.opacity =
        currentOpacity.current * (isHovered ? 1 : 0.85);
    }
  });

  // Generate a consistent color based on universe
  const cardColor = useMemo(() => {
    if (universe.color) return universe.color;
    const hue = (index * 137.5) % 360;
    return `hsl(${hue}, 40%, 60%)`;
  }, [universe.color, index]);

  // Create a simple pattern texture for the card face
  const patternTexture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 384;
    const ctx = canvas.getContext("2d")!;

    // Dark background
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid pattern
    ctx.strokeStyle = "rgba(230,147,188,0.03)";
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 30) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Node representations
    ctx.fillStyle = "rgba(230,147,188,0.08)";
    const nodes = [
      { x: 80, y: 80, w: 120, h: 70 },
      { x: 280, y: 120, w: 140, h: 80 },
      { x: 160, y: 240, w: 130, h: 75 },
      { x: 350, y: 280, w: 100, h: 60 },
    ];
    nodes.forEach((n) => {
      ctx.beginPath();
      ctx.roundRect(n.x, n.y, n.w, n.h, 6);
      ctx.fill();
    });

    // Connection lines
    ctx.strokeStyle = "rgba(230,147,188,0.06)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(200, 115);
    ctx.lineTo(280, 160);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(350, 200);
    ctx.lineTo(290, 240);
    ctx.stroke();

    // Active indicator for current workspace
    if (isActive) {
      ctx.fillStyle = "rgba(250, 15, 131, 0.3)";
      ctx.beginPath();
      ctx.arc(460, 40, 20, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "rgba(250, 15, 131, 0.8)";
      ctx.beginPath();
      ctx.arc(460, 40, 8, 0, Math.PI * 2);
      ctx.fill();
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
  }, [isActive, index]);

  return (
    <group
      ref={groupRef}
      position={[position[0], position[1], position[2]]}
      rotation={rotation}
    >
      {/* Main card body - paper thin with glass material */}
      <RoundedBox
        ref={meshRef}
        args={[CARD_WIDTH, CARD_HEIGHT, CARD_DEPTH]}
        radius={CARD_RADIUS}
        smoothness={4}
        onPointerEnter={(e) => {
          e.stopPropagation();
          onPointerEnter();
          document.body.style.cursor = "pointer";
        }}
        onPointerLeave={(e) => {
          e.stopPropagation();
          onPointerLeave();
          document.body.style.cursor = "auto";
        }}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        <meshPhysicalMaterial
          ref={materialRef}
          color="#e693bc"
          metalness={0.1}
          roughness={0.2}
          transmission={0.6}
          thickness={0.1}
          ior={1.5}
          transparent
          opacity={0.85}
          side={THREE.DoubleSide}
        />
      </RoundedBox>

      {/* Front face content plane */}
      <mesh position={[0, 0, CARD_DEPTH / 2 + 0.001]}>
        <planeGeometry args={[CARD_WIDTH - 0.1, CARD_HEIGHT - 0.1]} />
        <meshBasicMaterial
          map={patternTexture}
          transparent
          opacity={0.95}
          side={THREE.FrontSide}
        />
      </mesh>

      {/* Back face - mirror of front */}
      <mesh
        position={[0, 0, -CARD_DEPTH / 2 - 0.001]}
        rotation={[0, Math.PI, 0]}
      >
        <planeGeometry args={[CARD_WIDTH - 0.1, CARD_HEIGHT - 0.1]} />
        <meshBasicMaterial
          map={patternTexture}
          transparent
          opacity={0.7}
          side={THREE.FrontSide}
        />
      </mesh>

      {/* Subtle edge glow */}
      <mesh position={[0, CARD_HEIGHT / 2, 0]}>
        <boxGeometry args={[CARD_WIDTH, 0.01, CARD_DEPTH + 0.01]} />
        <meshStandardMaterial
          color={cardColor}
          emissive={cardColor}
          emissiveIntensity={isHovered ? 0.8 : 0.3}
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* Universe name label - use material props to fix depth/overlap issues */}
      <Text
        position={[0, -CARD_HEIGHT / 2 + 0.3, CARD_DEPTH / 2 + 0.08]}
        fontSize={0.14}
        color="#f0e4ea"
        anchorX="center"
        anchorY="middle"
        maxWidth={CARD_WIDTH - 0.4}
        material-toneMapped={false}
      >
        {universe.name}
      </Text>

      {/* Branch name sub-label */}
      {universe.branchName && (
        <Text
          position={[0, -CARD_HEIGHT / 2 + 0.14, CARD_DEPTH / 2 + 0.08]}
          fontSize={0.08}
          color="rgba(230,147,188,0.6)"
          anchorX="center"
          anchorY="middle"
          maxWidth={CARD_WIDTH - 0.4}
          material-toneMapped={false}
        >
          {universe.branchName}
        </Text>
      )}

      {/* Active workspace indicator */}
      {isActive && (
        <pointLight
          position={[0, 0, 0.2]}
          color="#fa0f83"
          intensity={isHovered ? 1.5 : 0.6}
          distance={2}
          decay={2}
        />
      )}

      {/* Hover glow */}
      {isHovered && (
        <pointLight
          position={[0, 0.3, 0.3]}
          color="#e693bc"
          intensity={1}
          distance={2.5}
          decay={2}
        />
      )}
    </group>
  );
}

export default GlassCard;
