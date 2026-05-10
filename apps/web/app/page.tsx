"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  AdaptationConfig,
  DEFAULT_ADAPTATION_CONFIG,
  MCQQuestion,
  RateRequest,
  RenderResponse,
} from "@/lib/types";
import { getRandomSeedPassage, SEED_PASSAGES } from "@/lib/seed_passages";
import { RollingAverage } from "@/lib/timing";
import { useScrollReveal } from "@/lib/useScrollReveal";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { configsEqual } from "@/lib/utils";
import {
  OnboardingTour,
  type OnboardingTourHandle,
} from "@/components/onboarding/OnboardingTour";
import {
  ConvergenceModal,
  detectStagnation,
  STAGNATION_MIN_SESSIONS,
} from "@/components/ConvergenceModal";

const USER_ID = "demo";
const MIN_WORD_COUNT = 50;
const CHOICE_LABELS = ["A", "B", "C", "D"] as const;

type Phase =
  | "idle"
  | "rendering"
  | "reading"
  | "loading_mcq"
  | "comprehension"
  | "submitting"
  | "done";

interface MCQState {
  question: MCQQuestion;
  selected: number | null; // 0–3 or null
}

/** One completed passage in the continuous optimization loop. */
interface LoopEntry {
  reward: number;
  config: AdaptationConfig;
  selfRating: number;
  mcqCorrect: boolean | null;
}

export default function ReaderPage() {
  const [text, setText] = useState("");
  const [textId, setTextId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [renderResponse, setRenderResponse] = useState<RenderResponse | null>(null);
  const [config, setConfig] = useState<AdaptationConfig>(DEFAULT_ADAPTATION_CONFIG);
  const [error, setError] = useState<string | null>(null);
  const [mcq, setMcq] = useState<MCQState | null>(null);
  const [mcqCorrect, setMcqCorrect] = useState<boolean | null>(null);
  const [selfRating, setSelfRating] = useState<number | null>(null);
  const [wasUserModified, setWasUserModified] = useState(false);
  const [rateResult, setRateResult] = useState<{ reward: number; event_id: number } | null>(null);

  // ── Continuous optimization loop ───────────────────────────────────────
  const [loopHistory, setLoopHistory] = useState<LoopEntry[]>([]);
  const [showConvergence, setShowConvergence] = useState(false);
  const [convergenceMean, setConvergenceMean] = useState(0);
  const [convergenceBestConfig, setConvergenceBestConfig] = useState<AdaptationConfig | null>(null);
  // Tracks which passage IDs have been used so far to avoid in-loop repeats
  const usedPassageIdsRef = useRef<Set<string>>(new Set());

  // ── Best Fit + run counter (persisted) ─────────────────────────────────
  const [bestFit, setBestFit, clearBestFit] = useLocalStorage<AdaptationConfig | null>(
    "lume_best_fit",
    null
  );
  const [configRuns, setConfigRuns] = useLocalStorage<number>("lume_config_runs", 0);

  // Hydrate config from Best Fit on first mount (run once, when localStorage hydrates)
  const bestFitAppliedRef = useRef(false);
  useEffect(() => {
    if (bestFitAppliedRef.current) return;
    if (bestFit !== null) {
      bestFitAppliedRef.current = true;
      const saved = bestFit;
      startTransition(() => {
        setConfig(saved);
        setWasUserModified(true);
      });
    }
  }, [bestFit]);

  // ── Header scroll shadow ────────────────────────────────────────────────
  const headerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const onScroll = () => {
      header.dataset.scrolled = window.scrollY > 8 ? "true" : "false";
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // ── Onboarding tour handle ──────────────────────────────────────────────
  const tourHandleRef = useRef<OnboardingTourHandle | null>(null);

  // ── WPM tracking ────────────────────────────────────────────────────────
  const startTimeRef = useRef<number | null>(null);
  const [wpm, setWpm] = useState<number | null>(null);

  const rollingAvgRef = useRef<RollingAverage>(new RollingAverage(5));
  const [rollingWpm, setRollingWpm] = useState<number | null>(null);

  // Top-k arm chips
  interface TopArm { arm_index: number; mean_reward: number; label: string }
  const [topArms, setTopArms] = useState<TopArm[] | null>(null);

  // ── Scroll-reveal hooks ─────────────────────────────────────────────────
  const { ref: heroRef, shown: heroShown } = useScrollReveal<HTMLDivElement>(0.1);
  const { ref: adaptRef, shown: adaptShown } = useScrollReveal<HTMLElement>(0.1);

  // ── Input validation ────────────────────────────────────────────────────
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  const isTextValid =
    text.trim().length > 0 &&
    text.length <= 10_000 &&
    wordCount >= MIN_WORD_COUNT;

  // ── Rolling WPM ticker ──────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "reading" || !renderResponse) return;
    const interval = setInterval(() => {
      if (startTimeRef.current === null) return;
      const elapsedMin = (Date.now() - startTimeRef.current) / 60_000;
      if (elapsedMin < 0.01) return;
      const instantWpm = Math.round(renderResponse.word_count / elapsedMin);
      const capped = Math.min(Math.max(instantWpm, 1), 600);
      rollingAvgRef.current.push(capped);
      setRollingWpm(Math.round(rollingAvgRef.current.average ?? capped));
    }, 2000);
    return () => clearInterval(interval);
  }, [phase, renderResponse]);

  // ── Load demo passage ───────────────────────────────────────────────────
  const loadDemoPassage = useCallback(() => {
    const passage = getRandomSeedPassage();
    setText(passage.text);
    setTextId(passage.id);
    setError(null);
  }, []);

  // ── Toggle adaptation ───────────────────────────────────────────────────
  const toggleAdaptation = useCallback(
    <K extends keyof AdaptationConfig>(key: K, value: AdaptationConfig[K]) => {
      setConfig((prev) => ({ ...prev, [key]: value }));
      setWasUserModified(true);
    },
    []
  );

  // ── Render ──────────────────────────────────────────────────────────────
  const handleRender = useCallback(async () => {
    if (!isTextValid) return;
    setPhase("rendering");
    setError(null);
    setRenderResponse(null);
    setMcq(null);
    setMcqCorrect(null);
    setSelfRating(null);
    startTimeRef.current = null;
    setWpm(null);
    rollingAvgRef.current.reset();
    setRollingWpm(null);

    // Increment run counter for user-modified configs
    if (wasUserModified) {
      setConfigRuns(configRuns + 1);
    }

    try {
      const body = {
        text: text.trim(),
        user_id: USER_ID,
        mode: "lume_tuned" as const,
        ...(wasUserModified
          ? {
              adaptation_config: config,
              arm_index: -1,
              recommendation_source: "user_override" as const,
            }
          : {}),
        text_id: textId,
      };

      const res = await fetch("/api/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error?.message ?? "Render failed");
      }

      setRenderResponse(data as RenderResponse);
      setConfig(data.adaptation_config);
      setPhase("reading");
      startTimeRef.current = Date.now();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Render failed");
      setPhase("idle");
    }
  }, [isTextValid, text, textId, config, wasUserModified, configRuns, setConfigRuns]);

  // ── Done reading → fetch MCQ ────────────────────────────────────────────
  const handleDoneReading = useCallback(async () => {
    if (startTimeRef.current && renderResponse) {
      const elapsedMs = Date.now() - startTimeRef.current;
      const elapsedMin = elapsedMs / 60_000;
      const calculatedWpm = Math.round(renderResponse.word_count / elapsedMin);
      setWpm(Math.min(Math.max(calculatedWpm, 1), 600));
    }

    setPhase("loading_mcq");
    setError(null);

    try {
      const res = await fetch("/api/generate-mcq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim(), text_id: textId }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error?.message ?? "Could not generate question");
      }

      setMcq({ question: data as MCQQuestion, selected: null });
      setPhase("comprehension");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not load comprehension question");
      setPhase("comprehension");
    }
  }, [renderResponse, text, textId]);

  // ── Submit MCQ + self-rating ────────────────────────────────────────────
  const handleSubmitAnswer = useCallback(async () => {
    if (!renderResponse || wpm === null) return;
    if (mcq !== null && mcq.selected === null) return;
    if (selfRating === null) return;

    setPhase("submitting");
    setError(null);

    const isCorrect = mcq ? mcq.selected === mcq.question.correct_index : null;
    setMcqCorrect(isCorrect);

    const rateReq: RateRequest = {
      render_id: renderResponse.render_id,
      user_id: USER_ID,
      adaptation_config: renderResponse.adaptation_config,
      arm_index: renderResponse.arm_index,
      recommendation_source: renderResponse.recommendation_source,
      was_user_modified: wasUserModified,
      wpm,
      comprehension_type: mcq !== null ? "both" : "self_rated",
      self_rating: selfRating,
      mcq_correct: isCorrect ?? undefined,
      text_id: renderResponse.text_id,
    };

    try {
      const res = await fetch("/api/rate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rateReq),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error?.message ?? "Rating failed");
      }

      if (!data.ok) {
        setError("Could not log this session (text may be too short).");
        setPhase("done");
        return;
      }

      setRateResult({ reward: data.reward, event_id: data.event_id });
      setPhase("done");

      // ── Continuous loop: record session + stagnation detection ─────────
      const entry: LoopEntry = {
        reward: data.reward,
        config: renderResponse.adaptation_config,
        selfRating: selfRating!,
        mcqCorrect: isCorrect,
      };
      // Use functional updater so we always get the latest history
      setLoopHistory((prev) => {
        const newHistory = [...prev, entry];

        // Run stagnation check on the growing reward curve
        const rewards = newHistory.map((e) => e.reward);
        const stag = detectStagnation(rewards);
        if (stag.isStagnant) {
          // Find the single best-performing config across all loop sessions
          const best = newHistory.reduce((a, b) => (a.reward > b.reward ? a : b));
          // Schedule via setTimeout so we don't set state inside a setState call
          setTimeout(() => {
            startTransition(() => {
              setConvergenceMean(stag.mean);
              setConvergenceBestConfig(best.config);
              setShowConvergence(true);
            });
          }, 800); // brief delay so done-screen renders first
        }

        return newHistory;
      });

      fetch(`/api/top-arms?user_id=${USER_ID}&k=3`)
        .then((r) => r.json())
        .then((d) => {
          if (d.top_arms && Array.isArray(d.top_arms)) {
            setTopArms(d.top_arms as TopArm[]);
          }
        })
        .catch(() => {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Rating submission failed");
      setPhase("done");
    }
  }, [renderResponse, wpm, mcq, selfRating, wasUserModified]);

  // ── Reset ───────────────────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setPhase("idle");
    setRenderResponse(null);
    setConfig(bestFit ?? DEFAULT_ADAPTATION_CONFIG);
    setError(null);
    setRateResult(null);
    setWpm(null);
    setMcq(null);
    setMcqCorrect(null);
    setSelfRating(null);
    setWasUserModified(bestFit !== null);
    setTopArms(null);
    rollingAvgRef.current.reset();
    setRollingWpm(null);
    startTimeRef.current = null;
    // Clear loop state on full reset
    setLoopHistory([]);
    setShowConvergence(false);
    usedPassageIdsRef.current.clear();
  }, [bestFit]);

  // ── Next Passage (continuous loop) ──────────────────────────────────────
  // Loads a fresh passage and lets the bandit pick the next config based on
  // its updated posteriors — no user_override, pure Thompson sampling.
  const handleNextPassage = useCallback(async () => {
    // Pick a passage not yet used in this loop session; cycle if exhausted
    const remaining = SEED_PASSAGES.filter(
      (p) => !usedPassageIdsRef.current.has(p.id)
    );
    const pool = remaining.length > 0 ? remaining : SEED_PASSAGES;
    const passage = pool[Math.floor(Math.random() * pool.length)];
    usedPassageIdsRef.current.add(passage.id);

    // Reset per-passage state
    setPhase("rendering");
    setRenderResponse(null);
    setMcq(null);
    setMcqCorrect(null);
    setSelfRating(null);
    setRateResult(null);
    setError(null);
    setWpm(null);
    setRollingWpm(null);
    startTimeRef.current = null;
    rollingAvgRef.current.reset();
    setText(passage.text);
    setTextId(passage.id);
    // Crucially: let the bandit Thompson-sample the next config
    setWasUserModified(false);

    try {
      const res = await fetch("/api/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: passage.text.trim(),
          user_id: USER_ID,
          mode: "lume_tuned" as const,
          text_id: passage.id,
          // No adaptation_config → bandit picks via Thompson sampling
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message ?? "Render failed");

      setRenderResponse(data as RenderResponse);
      setConfig(data.adaptation_config);
      setPhase("reading");
      startTimeRef.current = Date.now();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Render failed");
      setPhase("done");
    }
  }, []);

  // ── Convergence modal handlers ───────────────────────────────────────────
  const handleSaveAndExitLoop = useCallback(() => {
    if (convergenceBestConfig) {
      setBestFit(convergenceBestConfig);
    }
    setShowConvergence(false);
    // Full reset so the saved Best Fit hydrates on the idle screen
    setPhase("idle");
    setRenderResponse(null);
    setError(null);
    setRateResult(null);
    setWpm(null);
    setMcq(null);
    setMcqCorrect(null);
    setSelfRating(null);
    setWasUserModified(true); // best fit is now active
    setTopArms(null);
    rollingAvgRef.current.reset();
    setRollingWpm(null);
    startTimeRef.current = null;
    setLoopHistory([]);
    usedPassageIdsRef.current.clear();
  }, [convergenceBestConfig, setBestFit]);

  const handleKeepExploring = useCallback(() => {
    setShowConvergence(false);
  }, []);

  // ──────────────────────────────────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────────────────────────────────
  return (
    <>
      {/* ── Sticky glass header ── */}
      <header ref={headerRef} className="glass-bar sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
          {/* Logo + wordmark */}
          <div className="flex items-center gap-2.5">
            <div
              className="shrink-0 rounded-xl overflow-hidden"
              style={{
                width: 44,
                height: 44,
                border: "1px solid oklch(0.78 0.18 198 / 0.45)",
                boxShadow:
                  "0 0 10px oklch(0.78 0.18 198 / 0.30), 0 0 28px oklch(0.72 0.22 245 / 0.18), inset 0 0 8px oklch(0.72 0.22 245 / 0.08)",
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/lume-logo.png"
                alt=""
                className="w-full h-full object-cover scale-110"
                draggable={false}
              />
            </div>
            <span className="text-xl font-bold lume-wordmark" aria-label="Lume">
              lume
            </span>
          </div>

          {/* Right side: tagline + tour replay */}
          <div className="flex items-center gap-3">
            <p className="text-xs text-muted-foreground hidden sm:block tracking-wide">
              Adaptive reading · powered by AI
            </p>
            <button
              onClick={() => tourHandleRef.current?.replay()}
              aria-label="Replay onboarding tour"
              title="Replay tour"
              className="w-6 h-6 rounded-full border border-border/50 flex items-center justify-center text-xs text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
            >
              ?
            </button>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="max-w-3xl mx-auto px-4 pt-8 pb-16 flex flex-col gap-6 w-full">

        {/* ══════════════════════════════════
            IDLE — Hero + input
        ══════════════════════════════════ */}
        {phase === "idle" && (
          <section
            aria-label="Text input"
            className="flex flex-col gap-5"
          >
            {/* Hero text — scroll-reveal */}
            <div
              ref={heroRef}
              className="lume-reveal flex flex-col items-center gap-2 pt-4 pb-2"
              data-shown={heroShown ? "true" : "false"}
            >
              <h1
                className="text-4xl md:text-5xl font-bold lume-wordmark tracking-tight"
                style={{ letterSpacing: "-0.02em" }}
              >
                lume
              </h1>
              <p className="text-sm text-muted-foreground max-w-xs text-center leading-relaxed">
                Paste any passage and Lume personalises the typography for your unique reading profile
              </p>
            </div>

            {/* Textarea — glass card */}
            <div id="lume-reading-pane" className="glass-card rounded-2xl p-1.5">
              <Textarea
                id="paste-area"
                placeholder="Paste any text here  (≥ 50 words, ≤ 10 000 chars)…"
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  setTextId(null);
                  setError(null);
                }}
                rows={8}
                className="font-sans text-base resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 placeholder:text-muted-foreground/50"
                aria-label="Paste text to read"
                maxLength={10_000}
              />
            </div>

            {/* Action row */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <Button
                  onClick={loadDemoPassage}
                  variant="outline"
                  size="sm"
                  className="rounded-full border-border/60 hover:border-primary/40"
                >
                  Load demo passage
                </Button>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {wordCount} word{wordCount !== 1 ? "s" : ""}
                  {wordCount > 0 && wordCount < MIN_WORD_COUNT && (
                    <span className="text-destructive ml-1">
                      (need ≥{MIN_WORD_COUNT})
                    </span>
                  )}
                </span>
              </div>

              <Button
                onClick={handleRender}
                disabled={!isTextValid}
                className="btn-neon rounded-full px-6 h-9 gap-2"
                aria-label="Render passage with Lume"
              >
                Render with Lume
                <span aria-hidden="true">→</span>
              </Button>
            </div>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
          </section>
        )}

        {/* ══════════════════════════════════
            Adaptation panel — idle + reading
        ══════════════════════════════════ */}
        {(phase === "idle" || phase === "reading") && (
          <AdaptationPanel
            ref={adaptRef as React.RefObject<HTMLElement>}
            shown={adaptShown}
            config={config}
            onToggle={toggleAdaptation}
            disabled={phase !== "idle" && phase !== "reading"}
            bestFit={bestFit}
            configRuns={configRuns}
            onClearBestFit={clearBestFit}
          />
        )}

        {/* ══════════════════════════════════
            RENDERING spinner
        ══════════════════════════════════ */}
        {phase === "rendering" && (
          <div
            aria-live="polite"
            className="flex items-center gap-3 py-10 justify-center animate-in fade-in duration-300"
          >
            <span className="lume-spinner" aria-hidden="true" />
            <span className="text-sm text-muted-foreground">Rendering your text…</span>
          </div>
        )}

        {/* ══════════════════════════════════
            READING area
        ══════════════════════════════════ */}
        {phase === "reading" && renderResponse && (
          <section
            aria-label="Reading area"
            className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500"
            style={{ animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)" }}
          >
            {/* Passage card */}
            <div
              className={[
                "lume-reader glass-card rounded-2xl p-6 md:p-8",
                renderResponse.adaptation_config.color_overlay_on
                  ? "lume-reader--overlay"
                  : "",
                renderResponse.adaptation_config.opendyslexic_on
                  ? "lume-reader--opendyslexic"
                  : "",
              ]
                .filter(Boolean)
                .join(" ")}
              style={{
                letterSpacing:
                  renderResponse.adaptation_config.letter_spacing_em > 0
                    ? `${renderResponse.adaptation_config.letter_spacing_em}em`
                    : undefined,
                wordSpacing:
                  renderResponse.adaptation_config.word_spacing_em > 0
                    ? `${renderResponse.adaptation_config.word_spacing_em}em`
                    : undefined,
              }}
              aria-label="Rendered passage"
            >
              {renderResponse.tokens.map((token, i) => (
                <span key={i}>
                  {token.is_chunk_break && (
                    <span className="lume-chunk-break" aria-hidden="true" />
                  )}
                  <span
                    className={[
                      ...token.class_hints,
                      token.is_emphasized ? "lume-emphasis" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {token.text}
                  </span>
                  {" "}
                </span>
              ))}
            </div>

            {/* Meta bar */}
            <div className="flex items-center justify-between flex-wrap gap-2 px-1">
              <p className="text-xs text-muted-foreground">
                {renderResponse.recommendation_source} ·{" "}
                arm{" "}
                {renderResponse.arm_index === -1 ? "manual" : renderResponse.arm_index}
                {" "}· {renderResponse.word_count} words
              </p>
              {rollingWpm !== null && (
                <p
                  aria-live="polite"
                  aria-label={`Current reading speed: approximately ${rollingWpm} words per minute`}
                  className="text-xs font-semibold text-primary tabular-nums"
                >
                  ~{rollingWpm} WPM
                </p>
              )}
            </div>

            <Button
              onClick={handleDoneReading}
              className="btn-neon self-start rounded-full px-6 h-9 gap-2"
              aria-label="Finished reading — proceed to comprehension check"
            >
              I&apos;m done reading
              <span aria-hidden="true">→</span>
            </Button>
          </section>
        )}

        {/* ══════════════════════════════════
            LOADING MCQ spinner
        ══════════════════════════════════ */}
        {phase === "loading_mcq" && (
          <div
            aria-live="polite"
            className="flex items-center gap-3 py-10 justify-center animate-in fade-in duration-300"
          >
            <span className="lume-spinner" aria-hidden="true" />
            <span className="text-sm text-muted-foreground">Generating comprehension question…</span>
          </div>
        )}

        {/* ══════════════════════════════════
            COMPREHENSION — MCQ + slider
        ══════════════════════════════════ */}
        {phase === "comprehension" && (
          <section
            id="lume-comprehension-check"
            aria-label="Comprehension check"
            className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-3 duration-500"
            style={{ animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)" }}
          >
            {/* Header */}
            <div>
              <h2 className="text-lg font-semibold">Comprehension check</h2>
              {wpm !== null && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  Reading speed: ~<span className="text-primary font-medium tabular-nums">{wpm}</span> WPM
                </p>
              )}
            </div>

            {/* Part 1 — MCQ */}
            {mcq ? (
              <div className="glass-card rounded-2xl p-5">
                <p className="text-sm font-medium mb-4 leading-snug">
                  {mcq.question.question}
                </p>
                <div
                  role="radiogroup"
                  aria-label="Answer choices"
                  className="flex flex-col gap-2"
                >
                  {mcq.question.choices.map((choice, idx) => (
                    <label
                      key={idx}
                      className="lume-choice"
                      data-selected={mcq.selected === idx ? "true" : "false"}
                    >
                      <input
                        type="radio"
                        name="mcq-answer"
                        value={idx}
                        checked={mcq.selected === idx}
                        onChange={() =>
                          setMcq((prev) =>
                            prev ? { ...prev, selected: idx } : prev
                          )
                        }
                        className="sr-only"
                        aria-label={`Option ${CHOICE_LABELS[idx]}: ${choice}`}
                      />
                      <span className="lume-choice-badge" aria-hidden="true">
                        {CHOICE_LABELS[idx]}
                      </span>
                      <span className="text-sm leading-snug">{choice}</span>
                    </label>
                  ))}
                </div>
              </div>
            ) : (
              <div className="glass-card rounded-2xl p-5">
                <p className="text-sm text-muted-foreground">
                  Question unavailable — please rate your comprehension below.
                </p>
              </div>
            )}

            {/* Part 2 — Self-rating */}
            <div className="glass-card rounded-2xl p-5 flex flex-col gap-4">
              <p className="text-sm font-medium" id="self-rating-label">
                How well did you understand this passage?
              </p>

              <div
                role="group"
                aria-labelledby="self-rating-label"
                className="flex gap-2"
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setSelfRating(n)}
                    aria-label={`Rate ${n} out of 5`}
                    aria-pressed={selfRating === n}
                    className="flex-1 h-12 rounded-xl border text-sm font-bold transition-all"
                    style={
                      selfRating === n
                        ? {
                            borderColor: "oklch(0.78 0.18 198 / 0.7)",
                            background: "oklch(0.78 0.18 198 / 0.14)",
                            color: "oklch(0.82 0.18 198)",
                            boxShadow: "0 0 16px oklch(0.78 0.18 198 / 0.22)",
                          }
                        : {
                            borderColor: "oklch(0.75 0.14 198 / 0.18)",
                            background: "oklch(0.13 0.025 258 / 0.6)",
                            color: "oklch(0.55 0.04 258)",
                          }
                    }
                  >
                    {n}
                  </button>
                ))}
              </div>

              <div className="flex justify-between text-xs text-muted-foreground px-0.5">
                <span>Poor</span>
                <span>Excellent</span>
              </div>

              {selfRating !== null && (
                <div className="flex items-center gap-2" aria-live="polite">
                  <div className="flex gap-1 flex-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <div
                        key={n}
                        className="rating-pip"
                        data-filled={n <= selfRating ? "true" : "false"}
                        aria-hidden="true"
                      />
                    ))}
                  </div>
                  <span className="text-xs font-semibold text-primary tabular-nums shrink-0">
                    {selfRating} / 5
                  </span>
                </div>
              )}

              {selfRating === null && (
                <p className="text-xs text-muted-foreground text-center" aria-live="polite">
                  Tap a number to rate (required)
                </p>
              )}
            </div>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <Button
              onClick={handleSubmitAnswer}
              disabled={(mcq !== null && mcq.selected === null) || selfRating === null}
              className="btn-neon self-start rounded-full px-6 h-9 gap-2"
              aria-label="Submit comprehension answer and self-rating"
            >
              Submit answer
              <span aria-hidden="true">→</span>
            </Button>
          </section>
        )}

        {/* ══════════════════════════════════
            SUBMITTING spinner
        ══════════════════════════════════ */}
        {phase === "submitting" && (
          <div
            aria-live="polite"
            className="flex items-center gap-3 py-10 justify-center animate-in fade-in duration-300"
          >
            <span className="lume-spinner" aria-hidden="true" />
            <span className="text-sm text-muted-foreground">Submitting…</span>
          </div>
        )}

        {/* ══════════════════════════════════
            DONE — bento results
        ══════════════════════════════════ */}
        {phase === "done" && (
          <section
            aria-label="Session results"
            className="flex flex-col gap-5 animate-in fade-in slide-in-from-bottom-3 duration-600"
            style={{ animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)" }}
          >
            <div>
              <h2 className="text-lg font-semibold">Session complete</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Lume has updated your reading profile
              </p>
            </div>

            {/* ── Loop progress indicator ── */}
            {loopHistory.length > 0 && (
              <div
                className="glass-card rounded-xl px-4 py-3 flex items-center gap-3 animate-in fade-in duration-300"
                aria-label={`Optimization loop progress: ${loopHistory.length} session${loopHistory.length !== 1 ? "s" : ""} completed`}
              >
                <span className="text-xs text-muted-foreground shrink-0">
                  Loop · session {loopHistory.length}
                </span>
                {/* Reward sparkline — each dot encodes the reward magnitude */}
                <div className="flex gap-1 items-end flex-1" aria-hidden="true">
                  {loopHistory.map((e, i) => {
                    const h = Math.max(6, Math.round(e.reward * 28));
                    const hue = e.reward >= 0.65 ? "oklch(0.72 0.19 155)" : e.reward >= 0.45 ? "oklch(0.78 0.18 198)" : "oklch(0.55 0.04 258)";
                    return (
                      <div
                        key={i}
                        title={`Session ${i + 1}: ${(e.reward * 100).toFixed(0)}%`}
                        style={{
                          width: 6,
                          height: h,
                          borderRadius: 3,
                          background: hue,
                          transition: "height 240ms cubic-bezier(0.22, 1, 0.36, 1)",
                          flexShrink: 0,
                        }}
                      />
                    );
                  })}
                </div>
                {loopHistory.length >= STAGNATION_MIN_SESSIONS && (
                  <span
                    className="text-[10px] text-muted-foreground shrink-0 tabular-nums"
                    title="Lume is actively learning from your sessions"
                  >
                    learning…
                  </span>
                )}
              </div>
            )}

            {rateResult && (
              <>
                {/* Bento grid — staggered reveal */}
                <div className="bento-grid">
                  {/* WPM */}
                  <div
                    className="glass-card rounded-2xl p-5 flex flex-col gap-1 animate-in fade-in slide-in-from-bottom-2"
                    style={{ animationDuration: "500ms", animationDelay: "0ms", animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)", animationFillMode: "both" }}
                  >
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      Reading speed
                    </p>
                    <p className="text-3xl font-bold text-primary tabular-nums mt-1">
                      {wpm}
                    </p>
                    <p className="text-xs text-muted-foreground">words / min</p>
                  </div>

                  {/* MCQ result */}
                  <div
                    className="glass-card rounded-2xl p-5 flex flex-col gap-1 animate-in fade-in slide-in-from-bottom-2"
                    style={{ animationDuration: "500ms", animationDelay: "60ms", animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)", animationFillMode: "both" }}
                  >
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      MCQ
                    </p>
                    {mcqCorrect === true && (
                      <p className="text-2xl font-bold mt-1" style={{ color: "oklch(0.72 0.19 155)" }}>
                        ✓ Correct
                      </p>
                    )}
                    {mcqCorrect === false && (
                      <p className="text-2xl font-bold text-destructive mt-1">
                        ✗ Incorrect
                      </p>
                    )}
                    {mcqCorrect === null && (
                      <p className="text-sm text-muted-foreground mt-1">not assessed</p>
                    )}
                  </div>

                  {/* Self-rating */}
                  {selfRating !== null && (
                    <div
                      className="glass-card rounded-2xl p-5 flex flex-col gap-1 animate-in fade-in slide-in-from-bottom-2"
                      style={{ animationDuration: "500ms", animationDelay: "120ms", animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)", animationFillMode: "both" }}
                    >
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">
                        Self-rating
                      </p>
                      <div className="flex items-baseline gap-1 mt-1">
                        <span className="text-3xl font-bold text-primary tabular-nums">
                          {selfRating}
                        </span>
                        <span className="text-sm text-muted-foreground">/ 5</span>
                      </div>
                      <div className="flex gap-1 mt-2">
                        {[1, 2, 3, 4, 5].map((n) => (
                          <div
                            key={n}
                            className="rating-pip"
                            data-filled={n <= selfRating ? "true" : "false"}
                            aria-hidden="true"
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reward signal */}
                  <div
                    className="glass-card rounded-2xl p-5 flex flex-col gap-1 animate-in fade-in slide-in-from-bottom-2"
                    style={{ animationDuration: "500ms", animationDelay: "180ms", animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)", animationFillMode: "both" }}
                  >
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      Reward signal
                    </p>
                    <p className="text-3xl font-bold text-primary tabular-nums mt-1">
                      {(rateResult.reward * 100).toFixed(1)}
                      <span className="text-lg font-medium">%</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      event #{rateResult.event_id}
                    </p>
                  </div>

                  {/* Best Fit card */}
                  <div
                    className="glass-card rounded-2xl p-5 flex flex-col gap-2 animate-in fade-in slide-in-from-bottom-2"
                    style={{ animationDuration: "500ms", animationDelay: "240ms", animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)", animationFillMode: "both" }}
                  >
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      Best Fit
                    </p>
                    {bestFit &&
                    renderResponse &&
                    configsEqual(bestFit, renderResponse.adaptation_config) ? (
                      <p className="text-sm text-primary mt-0.5 font-medium">
                        ★ Saved as your Best Fit
                      </p>
                    ) : (
                      <>
                        {renderResponse && (
                          <Button
                            onClick={() => setBestFit(renderResponse.adaptation_config)}
                            size="sm"
                            className="btn-neon rounded-full px-4 h-8 text-xs self-start mt-0.5"
                            aria-label="Save current configuration as your Best Fit"
                          >
                            Set as My Best Fit
                          </Button>
                        )}
                        <p className="text-xs text-muted-foreground leading-snug">
                          Save this layout as your default for every future session.
                        </p>
                      </>
                    )}
                    {bestFit &&
                    renderResponse &&
                    !configsEqual(bestFit, renderResponse.adaptation_config) && (
                      <button
                        onClick={clearBestFit}
                        aria-label="Clear your saved Best Fit configuration"
                        className="text-xs text-muted-foreground underline underline-offset-2 self-start hover:text-foreground transition-colors"
                      >
                        Clear saved Best Fit
                      </button>
                    )}
                  </div>
                </div>

                {/* Wrong answer reveal */}
                {mcqCorrect === false && mcq && (
                  <div
                    className="glass-card rounded-2xl p-4 animate-in fade-in slide-in-from-bottom-1 duration-400"
                    style={{
                      borderLeft: "2px solid oklch(0.62 0.22 25 / 0.6)",
                      animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)",
                    }}
                  >
                    <p className="text-xs text-muted-foreground mb-1">
                      Correct answer was
                    </p>
                    <p className="text-sm">
                      &ldquo;{mcq.question.choices[mcq.question.correct_index]}&rdquo;
                    </p>
                  </div>
                )}
              </>
            )}

            {/* Top-k arm chips */}
            {topArms && topArms.length > 0 && (
              <div aria-label="Your top typographic configurations">
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                  Your best configurations so far
                </p>
                <div className="flex flex-wrap gap-2">
                  {topArms.map((arm, i) => (
                    <span
                      key={arm.arm_index}
                      className="lume-arm-chip neon-glow-teal animate-in fade-in slide-in-from-bottom-1"
                      style={{
                        animationDuration: "400ms",
                        animationDelay: `${i * 60}ms`,
                        animationTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)",
                        animationFillMode: "both",
                      }}
                      title={`Arm ${arm.arm_index} · mean reward ${(arm.mean_reward * 100).toFixed(1)}%`}
                    >
                      {arm.label}
                      <span className="text-primary font-semibold">
                        {(arm.mean_reward * 100).toFixed(0)}%
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            {/* ── Action row: loop continue + exit ── */}
            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={handleNextPassage}
                className="btn-neon rounded-full px-6 h-9 gap-2"
                aria-label="Load next passage and continue the optimization loop"
              >
                Next Passage
                <span aria-hidden="true">→</span>
              </Button>
              <Button
                onClick={handleReset}
                variant="outline"
                className="rounded-full px-6 h-9 gap-2 border-border/60 hover:border-primary/40"
                aria-label="Exit loop and start a new reading session"
              >
                <span aria-hidden="true">←</span>
                {loopHistory.length > 0 ? "Exit loop" : "Read another passage"}
              </Button>
            </div>
          </section>
        )}
      </main>

      {/* ── Convergence modal (portal-mounted, shown when loop converges) ── */}
      {showConvergence && convergenceBestConfig && (
        <ConvergenceModal
          bestConfig={convergenceBestConfig}
          meanReward={convergenceMean}
          sessionCount={loopHistory.length}
          onSaveAndExit={handleSaveAndExitLoop}
          onKeepExploring={handleKeepExploring}
        />
      )}

      {/* ── Onboarding tour (portal-mounted, runs once) ── */}
      <OnboardingTour handleRef={tourHandleRef} />
    </>
  );
}

// ── Adaptation Panel ──────────────────────────────────────────────────────

interface AdaptationPanelProps {
  config: AdaptationConfig;
  onToggle: <K extends keyof AdaptationConfig>(
    key: K,
    value: AdaptationConfig[K]
  ) => void;
  disabled: boolean;
  bestFit: AdaptationConfig | null;
  configRuns: number;
  onClearBestFit: () => void;
  shown?: boolean;
}

const AdaptationPanel = ({
  ref,
  config,
  onToggle,
  disabled,
  bestFit,
  configRuns,
  onClearBestFit,
  shown = true,
}: AdaptationPanelProps & { ref?: React.Ref<HTMLElement> }) => {
  const toggles: {
    key: keyof AdaptationConfig;
    label: string;
    isBoolean: boolean;
  }[] = [
    { key: "letter_spacing_em", label: "Letter spacing", isBoolean: false },
    { key: "word_spacing_em",   label: "Word spacing",   isBoolean: false },
    { key: "hyphenation_on",    label: "Hyphenation",    isBoolean: true  },
    { key: "emphasis_on",       label: "Emphasis",       isBoolean: true  },
    { key: "color_overlay_on",  label: "Warm overlay",   isBoolean: true  },
    { key: "chunked_on",        label: "Chunked",        isBoolean: true  },
    { key: "opendyslexic_on",   label: "OpenDyslexic",   isBoolean: true  },
  ];

  return (
    <section
      ref={ref}
      id="lume-text-config"
      aria-label="Adaptation controls"
      className={`glass-card rounded-2xl p-5 lume-reveal`}
      data-shown={shown ? "true" : "false"}
    >
      {/* Panel header */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Typographic adaptations
          </h2>
          {configRuns > 0 && (
            <span className="text-xs text-muted-foreground tabular-nums">
              {configRuns} iteration{configRuns !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        {bestFit && (
          <span className="lume-arm-chip neon-glow-teal text-xs flex items-center gap-1.5">
            <span aria-hidden="true">★</span>
            <span>Best Fit active</span>
            <button
              onClick={onClearBestFit}
              aria-label="Clear saved Best Fit"
              className="ml-0.5 hover:text-destructive transition-colors rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
            >
              ×
            </button>
          </span>
        )}
      </div>

      <div
        role="group"
        aria-label="Typography adaptation toggles"
        className="flex flex-wrap gap-2"
      >
        {toggles.map(({ key, label, isBoolean }) => {
          const isOn = isBoolean
            ? Boolean(config[key])
            : (config[key] as number) > 0;

          return (
            <label
              key={key}
              className="lume-toggle-pill"
              data-active={isOn ? "true" : "false"}
              data-disabled={disabled ? "true" : "false"}
            >
              <input
                type="checkbox"
                checked={isOn}
                disabled={disabled}
                onChange={(e) => {
                  if (isBoolean) {
                    onToggle(
                      key,
                      e.target.checked as AdaptationConfig[typeof key]
                    );
                  } else {
                    const onValue = key === "letter_spacing_em" ? 0.04 : 0.16;
                    onToggle(
                      key,
                      (e.target.checked
                        ? onValue
                        : 0.0) as AdaptationConfig[typeof key]
                    );
                  }
                }}
                className="sr-only"
                aria-label={label}
              />
              <span className="lume-toggle-dot" aria-hidden="true" />
              <span>{label}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
};
AdaptationPanel.displayName = "AdaptationPanel";
