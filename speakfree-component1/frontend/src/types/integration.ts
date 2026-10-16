// Types for the integrated pipeline (Components 2–4) – mirror backend/integration/routes.py
import type { PhonemeFinding, SessionSummary } from "../types";

export type Disorder = "normal" | "stuttering" | "dysarthria" | "articulation";
export type Focus = "fluency" | "motor_speech" | "speech_sounds" | "maintenance";

// ---------------------------------------------------------------- admin: pipeline overview
export interface PipelineRow {
  session_id: string;
  patient_id: string;
  patient_name: string;
  created_at: string;
  status: "completed" | "partial" | "failed";
  error: string | null;
  c1_overall_score: number | null;
  c1_severity_hint: number | null;
  articulation_score: number | null;
  primary_disorder: Disorder | null;
  severity_level: number | null;
  risk_level: string | null;
  therapy_focus: Focus | null;
}

export interface PipelineOverview {
  kpis: {
    sessions: number;
    completed: number;
    failed: number;
    average_articulation: number | null;
    disorders: Partial<Record<Disorder, number>>;
    severity: Record<string, number>;
    risk: Record<string, number>;
    therapy_attempts: number;
    active_patients_7d: number;
  };
  runs: PipelineRow[];
}

// ---------------------------------------------------------------- Component 2
export interface C2Articulation {
  status: "scored" | "insufficient_data";
  method?: "A_word_accuracy" | "B_confidence_clear_word_ratio";
  formula?: string;
  articulation_score?: number;
  articulation_level?: string;
  reliability?: string;
  reliability_flags?: string[];
  filler_count: number;
  fillers_removed?: string[];
  kept_word_count?: number;
  inputs?: Record<string, number | string | null>;
  message?: string;
}

export interface C2FluencyEvents {
  word_count: number;
  content_word_count: number;
  filler_count: number;
  word_repetition_count: number;
  phrase_repetition_count: number;
  prolongation_count: number;
  long_pause_count: number;
  longest_pause_sec: number;
  prolonged_words?: string[];
  filler_rate?: number;
  repetition_rate?: number;
  prolongation_rate?: number;
  long_pauses_per_min?: number;
}

export interface C2Report {
  component: string;
  schema_version: string;
  generated_at: string;
  session_articulation: {
    status: string;
    score: number | null;
    level: string | null;
    formula?: string;
    weights?: number[];
    scored_recordings: number;
    total_weighted_words?: number;
    pooled_confidence_C?: number | null;
    pooled_clear_word_ratio?: number | null;
    methods?: string[];
    reliability?: string;
    reliability_flags?: string[];
    min_recording_score?: number;
    max_recording_score?: number;
  };
  fluency_events: C2FluencyEvents;
  flagged_sounds: PhonemeFinding[];
  recordings: {
    analysis_id: string;
    task_type: string;
    task_id: string;
    title: string;
    transcript: string;
    duration_sec: number;
    articulation: C2Articulation;
    fluency_events: C2FluencyEvents;
  }[];
  ready_for_component3: boolean;
  component3_input: Record<string, unknown> | null;
}

// ---------------------------------------------------------------- Component 3
export interface FeatureImportance { feature: string; label: string; importance: number }

export interface C3Report {
  session_id: string;
  primary_disorder: Disorder;
  therapy_focus: Focus;
  severity_level: number;
  severity_label: string;
  risk_level: "Low" | "Medium" | "High";
  confidence_score: number;
  confidence_band: string;
  disorder_breakdown: Record<Disorder, number>;
  severity_breakdown: Record<string, number>;
  expected_level: number;
  stuttering_events: Record<"repetition" | "prolongation" | "block", number | null>;
  stuttering_positive_events: string[];
  stage1_acoustic: {
    status: string;
    probability: number | null;
    windows_used: number;
    per_window: { analysis_id: string; task_type: string; start_sec: number; probability: number }[];
    cv_metrics?: Record<string, unknown>;
  };
  feature_vector: { feature: string; label: string; value: number; imputed: boolean }[];
  feature_importance: { disorder_classifier: FeatureImportance[]; severity_estimator: FeatureImportance[] };
  flagged_sounds: { sound: string; accuracy_percent: number; status: string }[];
  uncertainty: {
    confidence_score: number;
    confidence_band: string;
    normalised_entropy: number;
    epistemic_std: number;
    temperature: number;
    method: string;
  };
  unified_score: {
    severity_level: number;
    severity_label: string;
    risk_level: string;
    confidence_score: number;
    scoring_method: string;
    scoring_explanation: string[];
    components_used: Record<string, number | string>;
  };
  professional_review_recommended: boolean;
  recommendations: string[];
  model_status: Record<string, string | boolean>;
  model_version: string;
  disclaimer: string;
  processing_time_seconds: number;
}

// ---------------------------------------------------------------- Component 4
export interface TherapyProfile {
  focus: Focus;
  focus_name: string;
  c3_disorder: Disorder;
  severity_level: number;
  severity_label: string;
  risk_level: string;
  confidence: number;
  focus_probabilities: Record<Focus, number>;
  flagged_sounds: string[];
  stuttering_events: string[];
  professional_review_recommended: boolean;
  start_level: string;
  created_at: string;
  source_session_id: string;
  baseline: {
    target_metric: { text: string; current: number; target: number; metric: string } | null;
    [key: string]: unknown;
  };
}

export interface PipelineDetail {
  session_id: string;
  status: string;
  error: string | null;
  created_at: string;
  patient: { id: string; full_name: string; age: number };
  stage_timings: Record<string, number>;
  c1_summary: SessionSummary;
  c2: C2Report | null;
  c3: C3Report | null;
  c4_profile: TherapyProfile | null;
}

export type ExerciseType =
  | "reading" | "pacing" | "daf" | "picture" | "clear_speech" | "loudness" | "sustained_vowel" | "sound_drill";

export interface Exercise {
  id: string;
  type: ExerciseType;
  title: string;
  description: string;
  level?: "beginner" | "intermediate" | "advanced";
  difficulty: number;
  focus: Focus[];
  target_wpm?: number;
  base_wpm?: number;
  passage?: string;
  prompts?: string[];
  image_url?: string;
  items?: string[];
  sound?: string;
  target_seconds?: number;
  times_practised: number;
  last_score: number | null;
  locked?: boolean;
  source?: "level" | "bandit";
  reason?: string;
  rank?: number;
}

export interface LevelState {
  level: string;
  level_index: number;
  label: string;
  next_level: string | null;
  start_level: string;
  strong_in_a_row: number;
  needed_to_advance: number;
  mastered: boolean;
  progress_text: string;
  strong_threshold: number;
  weak_threshold: number;
  history: { at: string | null; from: string | null; to: string; direction: string; reason: string }[];
}

export interface Goal {
  id: string;
  text: string;
  current: number | null;
  target: number;
  unit: string;
  met: boolean;
  screening_goal?: boolean;
}

export interface AttemptRecord {
  exercise_id: string;
  exercise_type: ExerciseType;
  title: string;
  level: string | null;
  duration_seconds: number;
  speaking_ratio: number | null;
  long_pauses: number;
  quiet_warnings: number;
  measured_wpm: number | null;
  target_wpm: number | null;
  max_phonation_sec: number | null;
  items_total: number | null;
  items_clear: number | null;
  self_rating: "easy" | "ok" | "hard";
  score: number;
  score_breakdown: { feature: string; label: string; value: number; weight: number; points: number }[];
  completed_at: string;
}

export interface ProgressSummary {
  has_data: boolean;
  total_sessions: number;
  total_minutes: number;
  average_score: number | null;
  best_score: number | null;
  streak_days: number;
  trend: { label: string; detail: string; delta: number };
  by_type: { type: string; label: string; attempts: number; average_score: number | null; best_score: number }[];
  recent: { exercise_id: string; title: string; score: number; verdict: string; completed_at: string; self_rating: string; exercise_type: string }[];
  history: { attempt: number; score: number; completed_at: string; title: string; exercise_type: string }[];
  daily: { date: string; sessions: number; average_score: number | null }[];
}

export interface TherapyPlan {
  has_profile: true;
  focus: { key: Focus; patient_name: string; tagline: string; techniques: string[]; ladder_type: ExerciseType };
  dose: { sessions_per_week: number; minutes_per_session: number; exercises_per_session: number };
  level: LevelState;
  today: Exercise[];
  week: { date: string; day: string; is_today: boolean; active: boolean; minutes: number; completed: number;
          exercises: { id: string; title: string; type: ExerciseType }[] }[];
  goals: Goal[];
  rescreen: { recommended: boolean; reasons: string[]; days_since_screening: number; attempts_since_screening: number;
              due_in_days: number; attempts_until_due: number };
  progress: ProgressSummary;
  library: Exercise[];
}

export type PlanResponse = TherapyPlan | { has_profile: false };

export interface BanditArm {
  id: string;
  title: string;
  type: ExerciseType;
  level: string | null;
  difficulty: number;
  focus: Focus[];
  times_practised: number;
  expected_reward: number;
  exploration_bonus: number;
  category_fit: number;
  category_prior: number;
  difficulty_fit: number;
  total: number;
  predicted_score: number | null;
  rank: number;
}

export interface AdminTherapy {
  patient: { id: string; full_name: string; age: number };
  profile: TherapyProfile | null;
  profile_history: { session_id: string; focus: Focus; severity_level: number; created_at: string }[];
  plan: (TherapyPlan & { engine: { context: { vector: number[]; labels: string[] }; arms: BanditArm[];
    focus_probabilities: Record<Focus, number>; attempts_since_screening: number } }) | null;
  attempts: AttemptRecord[];
  assistant_log: { question: string; reply: string; intent: string | null; confidence: number; source: string; created_at: string }[];
}

export interface AttemptPayload {
  exercise_id: string;
  live_session_id?: string;
  duration_seconds: number;
  speaking_ratio?: number;
  long_pauses?: number;
  quiet_warnings?: number;
  syllables?: number;
  target_wpm?: number;
  max_phonation_sec?: number;
  items_total?: number;
  items_clear?: number;
  self_rating: "easy" | "ok" | "hard";
}

export interface AttemptResult {
  record: AttemptRecord;
  score: number;
  verdict: string;
  feedback: string[];
  breakdown: AttemptRecord["score_breakdown"];
  level: LevelState;
  level_message: string | null;
  plan: TherapyPlan;
}

export interface Briefing {
  greeting: string;
  focus: { name: string; tagline: string; techniques: string[] };
  summary: string[];
  tip: string;
  next_step: { exercise_id: string; title: string; reason: string };
  suggestions: string[];
  llm_enabled: boolean;
}

export interface ChatReply {
  reply: string;
  action: { exercise_id?: string; href?: string; label: string } | null;
  suggestions: string[];
  intent: string | null;
  confidence: number;
  source: "classifier" | "llm" | "fallback";
}

export interface ModelsInfo {
  component2: { equations: { id: string; name: string; formula: string }[]; fillers: string[]; level_bands: { min: number; label: string }[] };
  component3: {
    health: { models_trained: string; models: Record<string, boolean>; model_version: string };
    model_card: {
      model_version: string;
      built_at: string;
      feature_order: string[];
      cascade: string[];
      disclaimer: string;
      models: Record<string, { algorithm: string; data_source: string; validation?: string; clinically_validated: boolean;
        built: boolean; metrics: Record<string, unknown> | null }>;
    } | null;
  };
  component4: {
    scoring_weights: Record<string, number>;
    thresholds: { strong: number; weak: number };
    bandit: { alpha: number; category_beta: number; difficulty_penalty: number; context_dim: number };
    dose_by_severity: Record<string, { sessions_per_week: number; minutes_per_session: number; exercises_per_session: number }>;
    start_level_by_severity: Record<string, string>;
    foci: Record<Focus, { admin_name: string; patient_name: string; ladder_type: string; c3_disorder: Disorder }>;
    intent_classifier: { examples: number; intents: number; accuracy: number; confidence_threshold: number };
  };
}
