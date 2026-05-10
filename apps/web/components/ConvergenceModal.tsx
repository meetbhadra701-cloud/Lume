"use client";

import { createPortal } from "react-dom";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import type { AdaptationConfig } from "@/lib/types";

// ─────────────────────────────────────────────────────────────────────────────
// Stagnation / convergence detection — pure math, no side-effects
// ─────────────────────────────────────────────────────────────────────────────

/** Minimum completed sessions before stagnation is ever evaluated. */
export const STAGNATION_MIN_SESSIONS = 3;

/**
 * Sliding-window size.  We look at the last N rewards to decide whether the
 * user has converged.  Keeping it at 3 means convergence is declared quickly
 * enough to be useful in a demo, but not so quickly that one lucky session
 * fires it.
 */
const STAGNATION_WINDOW = 3;

/**
 * Mean reward threshold.  Reward formula: 0.7·normWPM + 0.3·blendComprehension.
 * 0.65 is reachable at ~190 WPM with a 4/5 self-rating and a correct MCQ —
 * a realistic "good reading" baseline.
 */
const STAGNATION_MEAN_THRESHOLD = 0.65;

/**
 * Standard-deviation ceiling.  σ ≤ 0.08 means the last three sessions are
 * within ~8% of each other — genuinely stable, not random noise.
 */
const STAGNATION_STD_THRESHOLD = 0.08;

export interface StagnationResult {
  isStagnant: boolean;
  mean: number;   // mean reward of the window (0–1)
  std: number;    // population std-dev of the window
}

/**
 * Evaluate whether the reward curve has converged.
 *
 * Algorithm:
 *   1. Require at least STAGNATION_MIN_SESSIONS completed sessions.
 *   2. Take the last STAGNATION_WINDOW rewards.
 *   3. Compute population mean and std-dev.
 *   4. Stagnation iff mean ≥ MEAN_THRESHOLD AND std ≤ STD_THRESHOLD.
 *
 * This is essentially a lightweight run-length stability test on the reward
 * signal — cheap to compute, no model weights needed.
 */
export function detectStagnation(rewards: number[]): StagnationResult {
  if (rewards.length < STAGNATION_MIN_SESSIONS) {
    return { isStagnant: false, mean: 0, std: 0 };
  }

  const window = rewards.slice(-STAGNATION_WINDOW);
  const n = window.length;
  const mean = window.reduce((a, b) => a + b, 0) / n;
  const variance = window.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
  const std = Math.sqrt(variance);

  return {
    isStagnant: mean >= STAGNATION_MEAN_THRESHOLD && std <= STAGNATION_STD_THRESHOLD,
    mean,
    std,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Focus-trap helper
// ─────────────────────────────────────────────────────────────────────────────

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])';

function trapFocus(container: HTMLElement, e: KeyboardEvent) {
  if (e.key !== "Tab") return;
  const els = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE));
  if (els.length === 0) return;
  const first = els[0];
  const last = els[els.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) { e.preventDefault(); last.focus(); }
  } else {
    if (document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Config label helper
// ─────────────────────────────────────────────────────────────────────────────

function configLabel(config: AdaptationConfig): string {
  const parts: string[] = [];
  if (config.letter_spacing_em > 0) parts.push("Letter spacing");
  if (config.word_spacing_em > 0)   parts.push("Word spacing");
  if (config.hyphenation_on)        parts.push("Hyphenation");
  if (config.emphasis_on)           parts.push("Emphasis");
  if (config.color_overlay_on)      parts.push("Warm overlay");
  if (config.chunked_on)            parts.push("Chunked");
  if (config.opendyslexic_on)       parts.push("OpenDyslexic");
  return parts.length > 0 ? parts.join(" · ") : "Default (no adaptations)";
}

// ─────────────────────────────────────────────────────────────────────────────
// Modal component
// ─────────────────────────────────────────────────────────────────────────────

interface ConvergenceModalProps {
  /** The optimal config (highest-reward session's config). */
  bestConfig: AdaptationConfig;
  /** Mean reward of the convergence window (0–1). */
  meanReward: number;
  /** Number of loop sessions completed so far. */
  sessionCount: number;
  /** User clicked "Save as Best Fit and exit loop". */
  onSaveAndExit: () => void;
  /** User clicked "Keep exploring". */
  onKeepExploring: () => void;
}

export function ConvergenceModal({
  bestConfig,
  meanReward,
  sessionCount,
  onSaveAndExit,
  onKeepExploring,
}: ConvergenceModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Focus primary CTA on mount
  useEffect(() => {
    const t = setTimeout(() => {
      dialogRef.current
        ?.querySelector<HTMLElement>(FOCUSABLE)
        ?.focus();
    }, 50);
    return () => clearTimeout(t);
  }, []);

  // Escape = keep exploring
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onKeepExploring();
      if (dialogRef.current) trapFocus(dialogRef.current, e);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onKeepExploring]);

  if (typeof window === "undefined") return null;

  const content = (
    /* Backdrop */
    <div
      role="presentation"
      aria-hidden="false"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 10000,
        background: "rgba(6, 8, 16, 0.82)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        backdropFilter: "blur(4px)",
        animation: "lume-tooltip-in 240ms cubic-bezier(0.22, 1, 0.36, 1) both",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onKeepExploring(); }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="conv-title"
        aria-describedby="conv-desc"
        tabIndex={-1}
        className="glass-card rounded-2xl p-6 flex flex-col gap-5 shadow-2xl"
        style={{ maxWidth: 420, width: "100%", outline: "none" }}
      >
        {/* Icon + heading */}
        <div className="flex flex-col gap-2">
          <div
            aria-hidden="true"
            style={{
              fontSize: 36,
              lineHeight: 1,
              filter: "drop-shadow(0 0 12px oklch(0.78 0.18 198 / 0.6))",
            }}
          >
            🎯
          </div>
          <h2
            id="conv-title"
            className="text-lg font-bold"
            style={{ color: "oklch(0.82 0.18 198)" }}
          >
            Optimal format found
          </h2>
          <p id="conv-desc" className="text-sm text-muted-foreground leading-relaxed">
            After <strong className="text-foreground">{sessionCount}</strong> passages,
            Lume&apos;s AI has converged on the reading format that works best for you.
          </p>
        </div>

        {/* Stats row */}
        <div className="flex gap-3">
          <div
            className="flex-1 rounded-xl p-3 flex flex-col gap-1"
            style={{ background: "oklch(0.13 0.025 258 / 0.6)", border: "1px solid oklch(0.78 0.18 198 / 0.18)" }}
          >
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Avg reward
            </p>
            <p className="text-xl font-bold tabular-nums" style={{ color: "oklch(0.82 0.18 198)" }}>
              {(meanReward * 100).toFixed(1)}%
            </p>
          </div>
          <div
            className="flex-1 rounded-xl p-3 flex flex-col gap-1"
            style={{ background: "oklch(0.13 0.025 258 / 0.6)", border: "1px solid oklch(0.78 0.18 198 / 0.18)" }}
          >
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Sessions
            </p>
            <p className="text-xl font-bold tabular-nums" style={{ color: "oklch(0.82 0.18 198)" }}>
              {sessionCount}
            </p>
          </div>
        </div>

        {/* Recommended config */}
        <div
          className="rounded-xl p-4 flex flex-col gap-2"
          style={{ background: "oklch(0.13 0.025 258 / 0.6)", border: "1px solid oklch(0.25 0.03 258)" }}
        >
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
            Recommended configuration
          </p>
          <p className="text-sm text-foreground leading-relaxed font-medium">
            {configLabel(bestConfig)}
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-col gap-2">
          <Button
            onClick={onSaveAndExit}
            className="btn-neon rounded-full h-10 gap-2 w-full"
            aria-label="Save this configuration as your Best Fit and exit the loop"
          >
            <span aria-hidden="true">★</span>
            Save as Best Fit
          </Button>
          <button
            onClick={onKeepExploring}
            className="text-xs text-muted-foreground underline underline-offset-2 text-center hover:text-foreground transition-colors rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
            aria-label="Continue exploring more passages"
          >
            Keep exploring →
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
