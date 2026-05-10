"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface TourStep {
  readonly id: string;
  readonly title: string;
  readonly body: string;
}

/** Viewport-relative bounding box — mirrors DOMRect fields we need. */
export interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface Options {
  steps: readonly TourStep[];
  onFinish: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Safe localStorage
// ─────────────────────────────────────────────────────────────────────────────

function lsGet(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

function lsSet(key: string, val: string): void {
  try { localStorage.setItem(key, val); } catch { /* quota / private mode */ }
}

function lsRemove(key: string): void {
  try { localStorage.removeItem(key); } catch { /* ignore */ }
}

export const tourStorage = { get: lsGet, set: lsSet, remove: lsRemove };

// ─────────────────────────────────────────────────────────────────────────────
// Continuous position tracker
//
// Uses a requestAnimationFrame loop that:
//   • Calls getBoundingClientRect() every frame
//   • Diffs against the last known rect string to skip no-op updates
//   • Also watches for the element appearing via MutationObserver (SPA phase changes)
// ─────────────────────────────────────────────────────────────────────────────

type RectSetter = (r: TargetRect | null) => void;

function startTracking(targetId: string, setRect: RectSetter): () => void {
  let rafId = 0;
  let lastKey = "";
  let mutObs: MutationObserver | null = null;

  function sample(): void {
    const el = document.getElementById(targetId);
    if (!el) {
      if (lastKey !== "null") {
        lastKey = "null";
        startTransition(() => setRect(null));
      }
      return;
    }
    const r = el.getBoundingClientRect();
    // Truncate to integers — sub-pixel changes aren't meaningful for tour UI
    const key = `${Math.round(r.top)},${Math.round(r.left)},${Math.round(r.width)},${Math.round(r.height)}`;
    if (key !== lastKey) {
      lastKey = key;
      startTransition(() =>
        setRect({ top: r.top, left: r.left, width: r.width, height: r.height })
      );
    }
  }

  function tick(): void {
    sample();
    rafId = requestAnimationFrame(tick);
  }

  // Start the loop
  rafId = requestAnimationFrame(tick);

  // MutationObserver catches elements that appear/disappear due to React phase changes.
  // childList + subtree is enough; we don't need attribute tracking here.
  if (typeof MutationObserver !== "undefined") {
    mutObs = new MutationObserver(() => sample());
    mutObs.observe(document.body, { childList: true, subtree: true });
  }

  return () => {
    cancelAnimationFrame(rafId);
    mutObs?.disconnect();
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// scrollIntoView then settle
// ─────────────────────────────────────────────────────────────────────────────

function scrollToElement(id: string): void {
  const el = document.getElementById(id);
  if (!el) return;
  // Only scroll if not already fully in viewport
  const r = el.getBoundingClientRect();
  const inView = r.top >= 0 && r.bottom <= window.innerHeight;
  if (!inView) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────────────────────

export function useOnboardingTour({ steps, onFinish }: Options) {
  const [active, setActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const prevFocusRef = useRef<Element | null>(null);
  const stopTrackingRef = useRef<(() => void) | null>(null);

  // ── Start tracking the current step's target element ───────────────────────
  useEffect(() => {
    if (!active) return;
    const step = steps[stepIndex];
    if (!step) return;

    // Stop any prior tracking before starting fresh
    stopTrackingRef.current?.();

    // Attempt to scroll into view — fire-and-forget (smooth scroll is async)
    scrollToElement(step.id);

    // Start the RAF-based position tracker
    const stop = startTracking(step.id, setTargetRect);
    stopTrackingRef.current = stop;

    return () => {
      stop();
      stopTrackingRef.current = null;
    };
  }, [active, stepIndex, steps]);

  // ── Tour controls ──────────────────────────────────────────────────────────

  const start = useCallback(() => {
    if (typeof document !== "undefined") {
      prevFocusRef.current = document.activeElement;
    }
    setStepIndex(0);
    setTargetRect(null);
    setActive(true);
  }, []);

  const finish = useCallback(() => {
    stopTrackingRef.current?.();
    stopTrackingRef.current = null;
    onFinish();
    setActive(false);
    setTargetRect(null);
    if (prevFocusRef.current && "focus" in prevFocusRef.current) {
      (prevFocusRef.current as HTMLElement).focus();
    }
  }, [onFinish]);

  const next = useCallback(() => {
    if (stepIndex < steps.length - 1) {
      setStepIndex((i) => i + 1);
    } else {
      finish();
    }
  }, [stepIndex, steps.length, finish]);

  const back = useCallback(() => {
    if (stepIndex > 0) setStepIndex((i) => i - 1);
  }, [stepIndex]);

  const skip = finish;

  // ── Keyboard shortcuts (Esc / ← / →) ─────────────────────────────────────

  useEffect(() => {
    if (!active) return;
    const handler = (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          skip();
          break;
        case "ArrowRight":
          e.preventDefault();
          next();
          break;
        case "ArrowLeft":
          e.preventDefault();
          back();
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [active, next, back, skip]);

  // ── Public API ─────────────────────────────────────────────────────────────

  return {
    active,
    start,
    stepIndex,
    totalSteps: steps.length,
    currentStep: steps[stepIndex] as TourStep | undefined,
    targetRect,
    next,
    back,
    skip,
  };
}
