/**
 * TypeScript types for Lume API (mirrors Pydantic schemas in app/schemas.py)
 */

export interface TextFeatures {
  avg_word_len: number;
  syllable_density: number;
  freq_percentile_mean: number;
  sentence_count: number;
  flesch_kincaid: number;
}

export interface AdaptationConfig {
  letter_spacing_em: number;
  word_spacing_em: number;
  hyphenation_on: boolean;
  emphasis_on: boolean;
  color_overlay_on: boolean;
  chunked_on: boolean;
  opendyslexic_on: boolean;
}

export interface Token {
  text: string;
  is_emphasized: boolean;
  class_hints: string[];
  is_chunk_break: boolean;
}

export type RecommendationSource =
  | "bandit"
  | "model"
  | "demo_seed"
  | "mode_default"
  | "mode_bionic"
  | "mode_lume_tuned"
  | "user_override";

export interface RenderRequest {
  text: string;
  user_id: string;
  mode: "default" | "bionic" | "lume_tuned";
  adaptation_config?: AdaptationConfig | null;
  arm_index?: number | null;
  recommendation_source?: "user_override" | null;
  text_id?: string | null;
}

export interface RenderResponse {
  render_id: string;
  text_hash: string;
  text_id: string | null;
  features: TextFeatures;
  word_count: number;
  arm_index: number;
  adaptation_config: AdaptationConfig;
  recommendation_source: RecommendationSource;
  tokens: Token[];
  chunks: number[][];
}

export interface RateRequest {
  render_id: string;
  user_id: string;
  text_hash?: string | null;
  features_json?: Record<string, unknown> | null;
  word_count?: number | null;
  text_id?: string | null;
  adaptation_config: AdaptationConfig;
  arm_index: number;
  recommendation_source: RecommendationSource;
  was_user_modified: boolean;
  wpm: number;
  comprehension_score: number;
  comprehension_type: "mc" | "self_rated";
}

export interface RateResponse {
  ok: boolean;
  event_id: number;
  reward: number;
  next_recommendation: AdaptationConfig | null;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export const DEFAULT_ADAPTATION_CONFIG: AdaptationConfig = {
  letter_spacing_em: 0.0,
  word_spacing_em: 0.0,
  hyphenation_on: false,
  emphasis_on: false,
  color_overlay_on: false,
  chunked_on: false,
  opendyslexic_on: false,
};
