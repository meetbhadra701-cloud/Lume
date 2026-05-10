"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import type { TargetRect } from "@/lib/useOnboardingTour";
import { Button } from "@/components/ui/button";

// ─────────────────────────────────────────────────────────────────────────────
// Placement engine
// ─────────────────────────────────────────────────────────────────────────────

type Placement = "bottom" | "top" | "right" | "left" | "center";

interface ComputedPos {
  top: number;
  left: number;
  placement: Placement;
}

const TOOLTIP_MAX_W = 328;
const MARGIN = 16;   // min gap between tooltip and viewport edge
const GAP = 12;      // gap between tooltip and target element

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

/**
 * Computes the best tooltip position given:
 *  - targetRect  — live viewport-relative rect of the spotlit element
 *  - tooltipW/H  — ACTUAL rendered dimensions of the tooltip (measured post-render)
 *  - vw/vh       — current viewport size
 *
 * Tries placements in order: bottom → top → right → left → center (fallback).
 */
function computePlacement(
  target: TargetRect,
  tooltipW: number,
  tooltipH: number,
  vw: number,
  vh: number
): ComputedPos {
  const { top, left, width, height } = target;

  const centerX = left + width / 2;
  const centerY = top + height / 2;

  // Available space in each direction (accounting for the GAP)
  const spaceBottom = vh - top - height - GAP - MARGIN;
  const spaceTop    = top - GAP - MARGIN;
  const spaceRight  = vw - left - width - GAP - MARGIN;
  const spaceLeft   = left - GAP - MARGIN;

  // ── Try BELOW ────────────────────────────────────────────────────────────
  if (spaceBottom >= tooltipH) {
    return {
      top: top + height + GAP,
      left: clamp(centerX - tooltipW / 2, MARGIN, vw - tooltipW - MARGIN),
      placement: "bottom",
    };
  }

  // ── Try ABOVE ────────────────────────────────────────────────────────────
  if (spaceTop >= tooltipH) {
    return {
      top: top - tooltipH - GAP,
      left: clamp(centerX - tooltipW / 2, MARGIN, vw - tooltipW - MARGIN),
      placement: "top",
    };
  }

  // ── Try RIGHT ────────────────────────────────────────────────────────────
  if (spaceRight >= tooltipW) {
    return {
      top: clamp(centerY - tooltipH / 2, MARGIN, vh - tooltipH - MARGIN),
      left: left + width + GAP,
      placement: "right",
    };
  }

  // ── Try LEFT ─────────────────────────────────────────────────────────────
  if (spaceLeft >= tooltipW) {
    return {
      top: clamp(centerY - tooltipH / 2, MARGIN, vh - tooltipH - MARGIN),
      left: left - tooltipW - GAP,
      placement: "left",
    };
  }

  // ── Center fallback (no room in any direction) ────────────────────────────
  return {
    top: clamp(vh / 2 - tooltipH / 2, MARGIN, vh - tooltipH - MARGIN),
    left: clamp(vw / 2 - tooltipW / 2, MARGIN, vw - tooltipW - MARGIN),
    placement: "center",
  };
}

function centerPos(tooltipW: number, tooltipH: number, vw: number, vh: number): ComputedPos {
  return {
    top: clamp(vh / 2 - tooltipH / 2, MARGIN, vh - tooltipH - MARGIN),
    left: clamp(vw / 2 - tooltipW / 2, MARGIN, vw - tooltipW - MARGIN),
    placement: "center",
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Arrow indicator (points toward the target element)
// ─────────────────────────────────────────────────────────────────────────────

function Arrow({ placement }: { placement: Placement }) {
  if (placement === "center") return null;

  // Arrow points FROM tooltip TOWARD the target
  const arrowMap: Record<Placement, React.CSSProperties> = {
    bottom: {  // tooltip is below target → arrow points up
      top: -7,
      left: "50%",
      transform: "translateX(-50%)",
      borderLeft: "7px solid transparent",
      borderRight: "7px solid transparent",
      borderBottom: "7px solid oklch(0.17 0.030 258 / 0.95)",
    },
    top: {     // tooltip is above target → arrow points down
      bottom: -7,
      left: "50%",
      transform: "translateX(-50%)",
      borderLeft: "7px solid transparent",
      borderRight: "7px solid transparent",
      borderTop: "7px solid oklch(0.17 0.030 258 / 0.95)",
    },
    right: {   // tooltip is right of target → arrow points left
      top: "50%",
      left: -7,
      transform: "translateY(-50%)",
      borderTop: "7px solid transparent",
      borderBottom: "7px solid transparent",
      borderRight: "7px solid oklch(0.17 0.030 258 / 0.95)",
    },
    left: {    // tooltip is left of target → arrow points right
      top: "50%",
      right: -7,
      transform: "translateY(-50%)",
      borderTop: "7px solid transparent",
      borderBottom: "7px solid transparent",
      borderLeft: "7px solid oklch(0.17 0.030 258 / 0.95)",
    },
    center: {},
  };

  return (
    <div
      aria-hidden="true"
      style={{
        position: "absolute",
        width: 0,
        height: 0,
        pointerEvents: "none",
        ...arrowMap[placement],
      }}
    />
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Focus trap helper
// ─────────────────────────────────────────────────────────────────────────────

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

function trapFocus(container: HTMLElement, e: KeyboardEvent) {
  if (e.key !== "Tab") return;
  const focusable = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE));
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// TourTooltip component
// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  stepIndex: number;
  totalSteps: number;
  title: string;
  body: string;
  targetRect: TargetRect | null;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function TourTooltip({
  stepIndex,
  totalSteps,
  title,
  body,
  targetRect,
  onNext,
  onBack,
  onSkip,
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<ComputedPos | null>(null);
  const [visible, setVisible] = useState(false);

  /**
   * Two-phase positioning:
   *   Phase 1 — render tooltip invisible so we can measure its actual height.
   *   Phase 2 — useLayoutEffect measures, computes position, makes visible.
   *
   * This fires synchronously before the browser paints, so the user
   * never sees the tooltip in the wrong place.
   */
  useLayoutEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const tooltipW = Math.min(TOOLTIP_MAX_W, vw - MARGIN * 2);
    // Measure the ACTUAL rendered height (not an estimate)
    const tooltipH = el.offsetHeight;

    const newPos = targetRect
      ? computePlacement(targetRect, tooltipW, tooltipH, vw, vh)
      : centerPos(tooltipW, tooltipH, vw, vh);

    setPos(newPos);
    setVisible(true);
  }, [targetRect, stepIndex]); // Re-run when targetRect (live) or step changes

  // Note: visibility is reset by the parent passing key={stepIndex} to this component.
  // React unmounts+remounts on key change, so `visible` starts as false on each step.

  // Focus the first interactive element after positioning is done
  useEffect(() => {
    if (!visible || !dialogRef.current) return;
    const t = setTimeout(() => {
      const el = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE);
      el?.focus();
    }, 30);
    return () => clearTimeout(t);
  }, [visible, stepIndex]);

  // Trap Tab focus within the dialog
  const onKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (dialogRef.current) trapFocus(dialogRef.current, e.nativeEvent);
  }, []);

  if (typeof window === "undefined") return null;

  const vw = window.innerWidth;
  const tooltipW = Math.min(TOOLTIP_MAX_W, vw - MARGIN * 2);
  const isLast = stepIndex === totalSteps - 1;

  const content = (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-live="polite"
      aria-labelledby={`tour-title-${stepIndex}`}
      aria-describedby={`tour-body-${stepIndex}`}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      style={{
        position: "fixed",
        zIndex: 9999,
        width: tooltipW,
        top: pos ? pos.top : -9999,
        left: pos ? pos.left : -9999,
        // Phase 1: invisible (measuring). Phase 2: fade in.
        opacity: visible ? 1 : 0,
        pointerEvents: visible ? "auto" : "none",
        outline: "none",
        // Smooth position tracking when targetRect updates from RAF loop
        transition: visible
          ? [
              "top 80ms cubic-bezier(0.22, 1, 0.36, 1)",
              "left 80ms cubic-bezier(0.22, 1, 0.36, 1)",
              "opacity 200ms ease",
            ].join(", ")
          : "none",
        // Entry animation handled via opacity above; no separate keyframe needed
      }}
      className="glass-card rounded-2xl p-5 flex flex-col gap-3 shadow-2xl"
    >
      {/* Arrow pointing at target */}
      {pos && <Arrow placement={pos.placement} />}

      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-muted-foreground tabular-nums mb-0.5 uppercase tracking-wide">
            Step {stepIndex + 1} of {totalSteps}
          </p>
          <h3
            id={`tour-title-${stepIndex}`}
            className="text-sm font-semibold text-foreground leading-snug"
          >
            {title}
          </h3>
        </div>
        <button
          onClick={onSkip}
          aria-label="Close onboarding tour"
          className="shrink-0 -mt-0.5 -mr-1 p-1.5 rounded-lg text-muted-foreground hover:text-foreground transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M1 1l10 10M11 1L1 11" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <p
        id={`tour-body-${stepIndex}`}
        className="text-sm text-muted-foreground leading-relaxed"
      >
        {body}
      </p>

      {/* Progress pips */}
      <div
        role="progressbar"
        aria-valuenow={stepIndex + 1}
        aria-valuemin={1}
        aria-valuemax={totalSteps}
        aria-label={`Step ${stepIndex + 1} of ${totalSteps}`}
        className="flex gap-1.5 items-center"
      >
        {Array.from({ length: totalSteps }).map((_, i) => (
          <div
            key={i}
            aria-hidden="true"
            style={{
              height: "0.25rem",
              borderRadius: "9999px",
              transition: "width 240ms cubic-bezier(0.22, 1, 0.36, 1), background 200ms ease",
              width: i === stepIndex ? "1.375rem" : "0.375rem",
              background:
                i <= stepIndex
                  ? "oklch(0.78 0.18 198)"
                  : "oklch(0.25 0.025 258)",
            }}
          />
        ))}
      </div>

      {/* Action row */}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <button
          onClick={onSkip}
          className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2 transition-colors rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
        >
          Skip tour
        </button>
        <div className="flex items-center gap-2">
          {stepIndex > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={onBack}
              className="rounded-full px-3 h-7 text-xs"
              aria-label="Previous step"
            >
              ← Back
            </Button>
          )}
          <Button
            size="sm"
            onClick={onNext}
            className="btn-neon rounded-full px-4 h-7 text-xs"
            aria-label={isLast ? "Finish tour" : "Next step"}
          >
            {isLast ? "Got it ✓" : "Next →"}
          </Button>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
