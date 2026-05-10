"use client";

import { useCallback, useEffect, useRef } from "react";
import { SpotlightOverlay } from "./SpotlightOverlay";
import { TourTooltip } from "./TourTooltip";
import { useOnboardingTour, tourStorage } from "@/lib/useOnboardingTour";

// ─────────────────────────────────────────────────────────────────────────────
// Tour step definitions
// ─────────────────────────────────────────────────────────────────────────────

const TOUR_STEPS = [
  {
    id: "lume-text-config",
    title: "Tune your typography",
    body: "Toggle letter/word spacing, fonts, and contrast. Lume learns from every change and personalises future renders — so experiment freely.",
  },
  {
    id: "lume-reading-pane",
    title: "Your reading companion",
    body: "Paste any passage here and hit Render. Lume applies your current typography settings and tracks your reading speed automatically.",
  },
  {
    id: "lume-comprehension-check",
    title: "Quick understanding check",
    body: "After reading, answer a short question and rate your understanding. Both signals feed Lume's AI — your profile gets sharper every session.",
  },
] as const;

const LS_KEY = "lume_has_seen_tour";

// ─────────────────────────────────────────────────────────────────────────────
// Handle
// ─────────────────────────────────────────────────────────────────────────────

export interface OnboardingTourHandle {
  replay: () => void;
}

interface OnboardingTourProps {
  handleRef?: React.MutableRefObject<OnboardingTourHandle | null>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function OnboardingTour({ handleRef }: OnboardingTourProps) {
  // Track whether we've already decided to start (or not) on this mount.
  // Prevents the auto-trigger from re-firing on React StrictMode double-invocations.
  const didCheckRef = useRef(false);

  const handleFinish = useCallback(() => {
    tourStorage.set(LS_KEY, "true");
  }, []);

  const {
    active,
    start,
    stepIndex,
    totalSteps,
    currentStep,
    targetRect,
    next,
    back,
    skip,
  } = useOnboardingTour({ steps: TOUR_STEPS, onFinish: handleFinish });

  // ── Expose replay handle to parent (for the "?" button in the header) ──────
  useEffect(() => {
    if (!handleRef) return;
    handleRef.current = {
      replay: () => {
        tourStorage.remove(LS_KEY);
        start();
      },
    };
    // Cleanup on unmount
    return () => { if (handleRef.current) handleRef.current = null; };
  }, [handleRef, start]);

  // ── Auto-trigger on first visit ────────────────────────────────────────────
  //
  // Guards:
  //   1. `didCheckRef` — only check once per component mount
  //   2. `document.readyState` — wait until DOM is interactive/complete
  //   3. `localStorage` sentinel — skip if user has already seen the tour
  //
  useEffect(() => {
    if (didCheckRef.current) return;
    didCheckRef.current = true;

    function maybeStart() {
      if (tourStorage.get(LS_KEY)) return; // already seen
      // Small delay lets page layout settle (fonts, images) so element rects are accurate
      const t = setTimeout(start, 600);
      return t;
    }

    let timer: ReturnType<typeof setTimeout> | undefined;

    if (document.readyState === "loading") {
      // DOM not yet fully parsed — wait for DOMContentLoaded
      const onReady = () => { timer = maybeStart(); };
      document.addEventListener("DOMContentLoaded", onReady, { once: true });
      return () => {
        document.removeEventListener("DOMContentLoaded", onReady);
        if (timer) clearTimeout(timer);
      };
    } else {
      // DOM already ready (normal Next.js client navigation)
      timer = maybeStart();
      return () => { if (timer) clearTimeout(timer); };
    }
  }, [start]);

  // ── Re-check on tab focus (handles direct links in new tabs) ──────────────
  //
  // If the user opens Lume in a new tab (direct link) and the tour hasn't run,
  // `visibilitychange` fires when the tab becomes visible.
  //
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      if (active) return;           // tour already running
      if (tourStorage.get(LS_KEY)) return; // already seen
      start();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [active, start]);

  // ── Render ─────────────────────────────────────────────────────────────────

  if (!active || !currentStep) return null;

  return (
    <>
      <SpotlightOverlay targetRect={targetRect} />
      {/* key={stepIndex} causes React to fully remount TourTooltip on each step,
          resetting the two-phase visibility state (invisible-measure → visible) */}
      <TourTooltip
        key={stepIndex}
        stepIndex={stepIndex}
        totalSteps={totalSteps}
        title={currentStep.title}
        body={currentStep.body}
        targetRect={targetRect}
        onNext={next}
        onBack={back}
        onSkip={skip}
      />
    </>
  );
}
