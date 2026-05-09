"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  AdaptationConfig,
  DEFAULT_ADAPTATION_CONFIG,
  RateRequest,
  RenderResponse,
} from "@/lib/types";
import { getRandomSeedPassage } from "@/lib/seed_passages";
import { RollingAverage } from "@/lib/timing";

const USER_ID = "demo";
const MIN_WORD_COUNT = 50;

type Phase =
  | "idle"
  | "rendering"
  | "reading"
  | "comprehension"
  | "submitting"
  | "done";

interface ComprehensionState {
  type: "self_rated";
  rating: number; // 1–5
}

export default function ReaderPage() {
  const [text, setText] = useState("");
  const [textId, setTextId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [renderResponse, setRenderResponse] = useState<RenderResponse | null>(null);
  const [config, setConfig] = useState<AdaptationConfig>(DEFAULT_ADAPTATION_CONFIG);
  const [error, setError] = useState<string | null>(null);
  const [comprehension, setComprehension] = useState<ComprehensionState>({ type: "self_rated", rating: 3 });
  const [wasUserModified, setWasUserModified] = useState(false);
  const [rateResult, setRateResult] = useState<{ reward: number; event_id: number } | null>(null);

  // WPM tracking
  const startTimeRef = useRef<number | null>(null);
  const [wpm, setWpm] = useState<number | null>(null);

  // Rolling WPM display (sliding window, §DSA_INVENTORY — RollingAverage O(1))
  const rollingAvgRef = useRef<RollingAverage>(new RollingAverage(5));
  const [rollingWpm, setRollingWpm] = useState<number | null>(null);

  // Top-k arm chips
  interface TopArm { arm_index: number; mean_reward: number; label: string }
  const [topArms, setTopArms] = useState<TopArm[] | null>(null);

  // Input validation
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  const isTextValid =
    text.trim().length > 0 &&
    text.length <= 10_000 &&
    wordCount >= MIN_WORD_COUNT;

  // Rolling WPM ticker — updates every 2s while reading
  useEffect(() => {
    if (phase !== "reading" || !renderResponse) return;
    const interval = setInterval(() => {
      if (startTimeRef.current === null) return;
      const elapsedMin = (Date.now() - startTimeRef.current) / 60_000;
      if (elapsedMin < 0.01) return; // avoid absurd values in first 600ms
      const instantWpm = Math.round(renderResponse.word_count / elapsedMin);
      const capped = Math.min(Math.max(instantWpm, 1), 600);
      rollingAvgRef.current.push(capped);
      setRollingWpm(Math.round(rollingAvgRef.current.average ?? capped));
    }, 2000);
    return () => clearInterval(interval);
  }, [phase, renderResponse]);

  // Load demo passage
  const loadDemoPassage = useCallback(() => {
    const passage = getRandomSeedPassage();
    setText(passage.text);
    setTextId(passage.id);
    setError(null);
  }, []);

  // Toggle adaptation
  const toggleAdaptation = useCallback(
    <K extends keyof AdaptationConfig>(key: K, value: AdaptationConfig[K]) => {
      setConfig((prev) => ({ ...prev, [key]: value }));
      setWasUserModified(true);
    },
    []
  );

  // Render
  const handleRender = useCallback(async () => {
    if (!isTextValid) return;
    setPhase("rendering");
    setError(null);
    setRenderResponse(null);
    startTimeRef.current = null;
    setWpm(null);
    rollingAvgRef.current.reset();
    setRollingWpm(null);

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
  }, [isTextValid, text, textId, config, wasUserModified]);

  // Done reading
  const handleDoneReading = useCallback(() => {
    if (startTimeRef.current && renderResponse) {
      const elapsedMs = Date.now() - startTimeRef.current;
      const elapsedMin = elapsedMs / 60_000;
      const calculatedWpm = Math.round(renderResponse.word_count / elapsedMin);
      setWpm(Math.min(Math.max(calculatedWpm, 1), 600));
    }
    setPhase("comprehension");
  }, [renderResponse]);

  // Submit rating
  const handleSubmitRating = useCallback(async () => {
    if (!renderResponse || wpm === null) return;
    setPhase("submitting");
    setError(null);

    const comprehensionScore = (comprehension.rating - 1) / 4;

    const rateReq: RateRequest = {
      render_id: renderResponse.render_id,
      user_id: USER_ID,
      adaptation_config: renderResponse.adaptation_config,
      arm_index: renderResponse.arm_index,
      recommendation_source: renderResponse.recommendation_source,
      was_user_modified: wasUserModified,
      wpm,
      comprehension_score: comprehensionScore,
      comprehension_type: "self_rated",
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

      // Fetch top-k arm chips (uses AdaptationHeap DSA on backend)
      fetch(`/api/top-arms?user_id=${USER_ID}&k=3`)
        .then((r) => r.json())
        .then((d) => {
          if (d.top_arms && Array.isArray(d.top_arms)) {
            setTopArms(d.top_arms as TopArm[]);
          }
        })
        .catch(() => {}); // non-critical; chips just won't show
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Rating submission failed");
      setPhase("done");
    }
  }, [renderResponse, wpm, comprehension, wasUserModified]);

  // Reset
  const handleReset = useCallback(() => {
    setPhase("idle");
    setRenderResponse(null);
    setConfig(DEFAULT_ADAPTATION_CONFIG);
    setError(null);
    setRateResult(null);
    setWpm(null);
    setWasUserModified(false);
    setTopArms(null);
    rollingAvgRef.current.reset();
    setRollingWpm(null);
    startTimeRef.current = null;
  }, []);

  return (
    <main className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Lume</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Personalized reading accessibility for dyslexia
        </p>
      </header>

      {/* Paste area */}
      {phase === "idle" && (
        <section aria-label="Text input" className="flex flex-col gap-3">
          <Textarea
            id="paste-area"
            placeholder="Paste any text here (≥50 words, ≤10,000 chars)…"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setTextId(null);
              setError(null);
            }}
            rows={8}
            className="font-sans text-base resize-none"
            aria-label="Paste text to read"
            maxLength={10_000}
          />

          <div className="flex items-center gap-2 flex-wrap">
            <Button
              onClick={loadDemoPassage}
              variant="outline"
              size="sm"
            >
              Load demo passage
            </Button>
            <span className="text-xs text-muted-foreground">
              {wordCount} word{wordCount !== 1 ? "s" : ""}
              {wordCount > 0 && wordCount < MIN_WORD_COUNT && (
                <span className="text-destructive ml-1">
                  (need ≥{MIN_WORD_COUNT})
                </span>
              )}
            </span>
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button
            onClick={handleRender}
            disabled={!isTextValid}
            className="self-start"
          >
            Render with Lume
          </Button>
        </section>
      )}

      {/* Adaptation toggles */}
      {(phase === "idle" || phase === "reading") && (
        <AdaptationPanel
          config={config}
          onToggle={toggleAdaptation}
          disabled={phase !== "idle" && phase !== "reading"}
        />
      )}

      {/* Reading area */}
      {phase === "reading" && renderResponse && (
        <section aria-label="Reading area" className="flex flex-col gap-4">
          <div
            className={[
              "lume-reader rounded-lg p-6 border",
              renderResponse.adaptation_config.color_overlay_on
                ? "lume-reader--overlay"
                : "bg-card",
              renderResponse.adaptation_config.opendyslexic_on
                ? "lume-reader--opendyslexic"
                : "",
            ].join(" ")}
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

          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-xs text-muted-foreground">
              Recommendation: {renderResponse.recommendation_source} · Arm:{" "}
              {renderResponse.arm_index === -1
                ? "manual"
                : renderResponse.arm_index}{" "}
              · {renderResponse.word_count} words
            </p>
            {rollingWpm !== null && (
              <p
                aria-live="polite"
                aria-label={`Current reading speed: approximately ${rollingWpm} words per minute`}
                className="text-xs font-medium text-muted-foreground tabular-nums"
              >
                ~{rollingWpm} WPM
              </p>
            )}
          </div>

          <Button
            onClick={handleDoneReading}
            className="self-start"
            aria-label="Finished reading — proceed to comprehension check"
          >
            I&apos;m done reading
          </Button>
        </section>
      )}

      {/* Comprehension */}
      {phase === "comprehension" && (
        <section
          aria-label="Comprehension rating"
          className="flex flex-col gap-4"
        >
          <div>
            <h2 className="text-lg font-semibold mb-1">
              How well did you understand the text?
            </h2>
            {wpm !== null && (
              <p className="text-sm text-muted-foreground">
                Estimated reading speed: ~{wpm} WPM
              </p>
            )}
          </div>

          <fieldset className="border rounded-lg p-4">
            <legend className="text-sm font-medium px-1">
              Self-rated comprehension (1 = very poor, 5 = excellent)
            </legend>
            <div className="flex gap-3 mt-3">
              {[1, 2, 3, 4, 5].map((n) => (
                <label
                  key={n}
                  className="flex flex-col items-center gap-1 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="comprehension"
                    value={n}
                    checked={comprehension.rating === n}
                    onChange={() =>
                      setComprehension({ type: "self_rated", rating: n })
                    }
                    className="w-4 h-4"
                    aria-label={`${n} out of 5`}
                  />
                  <span className="text-sm">{n}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <Button
            onClick={handleSubmitRating}
            className="self-start"
            aria-label="Submit comprehension rating"
          >
            Submit
          </Button>
        </section>
      )}

      {/* Results */}
      {phase === "done" && (
        <section aria-label="Session results" className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Session complete</h2>
          {rateResult && (
            <div className="text-sm space-y-1">
              <p>
                <span className="font-medium">Reading speed:</span> {wpm} WPM
              </p>
              <p>
                <span className="font-medium">Comprehension:</span>{" "}
                {comprehension.rating}/5
              </p>
              <p>
                <span className="font-medium">Reward signal:</span>{" "}
                {(rateResult.reward * 100).toFixed(1)}%
              </p>
              <p className="text-muted-foreground text-xs">
                Event #{rateResult.event_id} logged. Lume is learning your
                preferences.
              </p>
            </div>
          )}

          {/* Top-k arm chips — uses AdaptationHeap DSA on backend (§DSA_INVENTORY) */}
          {topArms && topArms.length > 0 && (
            <div
              aria-label="Your top typographic configurations"
              className="mt-2"
            >
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Your best configurations so far:
              </p>
              <div className="flex flex-wrap gap-2">
                {topArms.map((arm) => (
                  <span
                    key={arm.arm_index}
                    className="inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium"
                    title={`Arm ${arm.arm_index} · mean reward ${(arm.mean_reward * 100).toFixed(1)}%`}
                  >
                    {arm.label}
                    <span className="text-muted-foreground">
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
          <Button
            onClick={handleReset}
            variant="outline"
            className="self-start"
            aria-label="Start a new reading session"
          >
            Read another passage
          </Button>
        </section>
      )}

      {phase === "rendering" && (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          Rendering your text…
        </p>
      )}
      {phase === "submitting" && (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          Submitting…
        </p>
      )}
    </main>
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
}

function AdaptationPanel({ config, onToggle, disabled }: AdaptationPanelProps) {
  const toggles: {
    key: keyof AdaptationConfig;
    label: string;
    isBoolean: boolean;
  }[] = [
    { key: "letter_spacing_em", label: "Letter spacing", isBoolean: false },
    { key: "word_spacing_em", label: "Word spacing", isBoolean: false },
    { key: "hyphenation_on", label: "Hyphenation", isBoolean: true },
    { key: "emphasis_on", label: "Reading emphasis", isBoolean: true },
    { key: "color_overlay_on", label: "Warm overlay", isBoolean: true },
    { key: "chunked_on", label: "Chunked reading", isBoolean: true },
    { key: "opendyslexic_on", label: "OpenDyslexic font", isBoolean: true },
  ];

  return (
    <section
      aria-label="Adaptation controls"
      className="border rounded-lg p-4"
    >
      <h2 className="text-sm font-semibold mb-3">Adaptations</h2>
      <div
        role="group"
        aria-label="Typography adaptation toggles"
        className="grid grid-cols-2 sm:grid-cols-3 gap-2"
      >
        {toggles.map(({ key, label, isBoolean }) => {
          const isOn = isBoolean
            ? Boolean(config[key])
            : (config[key] as number) > 0;

          return (
            <label
              key={key}
              className="flex items-center gap-2 text-sm cursor-pointer"
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
                className="w-4 h-4"
                aria-label={label}
              />
              <span>{label}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}
