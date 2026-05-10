"use client";

import { startTransition, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { TargetRect } from "@/lib/useOnboardingTour";

interface Props {
  targetRect: TargetRect | null;
}

const PAD = 10;          // padding around the spotlit element
const RADIUS = 16;       // border-radius of the cutout
const SHADOW_SPREAD = 9999; // large enough to cover any viewport

/**
 * Spotlight overlay using the box-shadow technique:
 *   A transparent div is positioned over the target element.
 *   An outward box-shadow with a huge spread covers the rest of the screen.
 *   CSS transitions on top/left/width/height make it track smoothly.
 *
 * Advantages over SVG mask:
 *   • CSS transitions work natively on positional properties
 *   • No SVG viewBox repaints on every RAF tick
 *   • Handles border-radius correctly
 */
export function SpotlightOverlay({ targetRect }: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    startTransition(() => setMounted(true));
  }, []);

  if (!mounted) return null;

  const hasTarget = targetRect !== null;

  // When there is no target, collapse the hole to the center of the screen so
  // the box-shadow still covers everything (visible as a pure dark backdrop).
  const holeStyle: React.CSSProperties = hasTarget
    ? {
        position: "fixed",
        top: targetRect.top - PAD,
        left: targetRect.left - PAD,
        width: targetRect.width + PAD * 2,
        height: targetRect.height + PAD * 2,
        borderRadius: RADIUS,
        // The massive outward box-shadow IS the dark backdrop
        boxShadow: `0 0 0 ${SHADOW_SPREAD}px rgba(6, 8, 16, 0.85)`,
        // Glow ring via outline
        outline: "1.5px solid rgba(96, 210, 215, 0.75)",
        outlineOffset: "2px",
        // Smooth tracking follows the RAF-updated rect
        transition: [
          "top 80ms cubic-bezier(0.22, 1, 0.36, 1)",
          "left 80ms cubic-bezier(0.22, 1, 0.36, 1)",
          "width 80ms cubic-bezier(0.22, 1, 0.36, 1)",
          "height 80ms cubic-bezier(0.22, 1, 0.36, 1)",
        ].join(", "),
        zIndex: 9990,
        pointerEvents: "none",
        animation: "lume-ring-glow 2.4s ease-in-out infinite",
      }
    : {
        // No target — full-screen dark overlay, no cutout
        position: "fixed",
        inset: 0,
        background: "rgba(6, 8, 16, 0.85)",
        zIndex: 9990,
        pointerEvents: "none",
      };

  return createPortal(
    <div aria-hidden="true" style={holeStyle} />,
    document.body
  );
}
