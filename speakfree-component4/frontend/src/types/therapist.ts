import {
  AssistantReply,
  ExerciseType,
  GoalMetric,
  LevelState,
  ProgressSummary,
  ReadingLevel,
  ReportCard,
  ScorePart,
  Screening,
  SelfRating,
  WeeklyPlanResponse,
} from "./therapy";

export type { GoalMetric };

export type StudentStatusKey =
  | "not_started"
  | "inactive"
  | "needs_attention"
  | "improving"
  | "on_track";

export interface StudentStatus {
  key: StudentStatusKey;
  label: string;
  detail: string;
}

export interface StudentRow {
  email: string;
  name: string;
  registered_at: string | null;
  last_active: string | null;
  total_sessions: number;
  total_minutes: number;
  average_score: number | null;
  latest_score: number | null;
  level: ReadingLevel;
  level_label: string;
  streak_days: number;
  status: StudentStatus;
}

export interface CaseloadOverview {
  alerts: { email: string; name: string; status: StudentStatus }[];
  total_students: number;
  active_this_week: number;
  sessions_this_week: number;
  total_sessions: number;
  average_score: number | null;
  needs_attention: number;
  recent_session_times: string[];
  level_distribution: { level: ReadingLevel; label: string; students: number }[];
}

export interface ExpertReview {
  rating: number;
  note: string | null;
  by: string;
  at: string;
  source?: "clinician" | "synthetic";
}

export interface StudentRecord {
  id: string;
  exercise_id: string;
  expert: ExpertReview | null;
  expert_reviews: ExpertReview[];
  measured_wpm: number | null;
  target_wpm: number | null;
  score_breakdown: ScorePart[];
  completed_at: string;
  title: string;
  exercise_type: ExerciseType;
  level: ReadingLevel | null;
  duration_seconds: number;
  speaking_ratio: number | null;
  long_pauses: number;
  self_rating: SelfRating;
  score: number;
  verdict: string;
}

export interface StudentDetail {
  profile: {
    email: string;
    name: string;
    registered_at: string | null;
    last_login: string | null;
  };
  row: StudentRow;
  summary: ProgressSummary;
  score_history: { attempt: number; date: string; score: number; title: string }[];
  weekly_sessions: { label: string; sessions: number; minutes: number }[];
  records: StudentRecord[];
  settings: TherapistSettings;
  plan: Omit<WeeklyPlanResponse, "user_id">;
  plan_reviews: PlanReview[];
}

export type RatingSource = "clinician" | "synthetic";
export type PlanVerdict = "appropriate" | "partly" | "not_appropriate";

export interface PlanReview {
  id: string;
  student: string;
  verdict: PlanVerdict;
  note: string | null;
  by: string;
  at: string;
  source: RatingSource;
  plan: { level: string; exercises: { id: string; title: string; source: string }[] };
}

export interface TherapistSettings {
  assigned: { exercise_id: string; by: string; at: string }[];
  level_override: { level: ReadingLevel; by: string; at: string } | null;
  goals: { id: string; metric: GoalMetric; target: number }[];
  notes: { id: string; text: string; by: string; at: string }[];
  screening: Screening | null;
}

export interface FitMetrics {
  mae: number;
  rmse: number;
  pearson_r: number | null;
  within_15: number;
}

export interface StrongMatch {
  based_on: string;
  threshold: number;
  n: number;
  expert_good: number;
  flagged_strong: number;
  accuracy: number;
  sensitivity: number | null;
  specificity: number | null;
}

export interface InterRater {
  n_pairs: number;
  exact_agreement: number | null;
  within_one: number | null;
  kappa: number | null;
  weighted_kappa: number | null;
}

export interface SourceValidation {
  n: number;
  shown_scores: FitMetrics;
  prior_model: FitMetrics;
  calibrated_model_loo: FitMetrics | null;
  strong_match: StrongMatch;
  inter_rater: InterRater;
}

export interface PlanValidationStats {
  n: number;
  students: number;
  counts: Record<PlanVerdict, number>;
  appropriate_pct: number | null;
  acceptable_pct: number | null;
}

export interface EvidenceReport {
  scoring: {
    active: "prior" | "calibrated";
    data_source: RatingSource | null;
    n_clinician: number;
    n_synthetic: number;
    validation_by_source: Record<RatingSource, SourceValidation | null>;
    n_ratings: number;
    min_ratings: number;
    ridge_lambda?: number;
    fitted_at?: string;
    thresholds: { strong: number; weak: number };
    prior_thresholds: { strong: number; weak: number };
    threshold_accuracy: { strong: number | null; weak: number | null };
    features: { feature: string; label: string; prior: number; current: number }[];
    validation: {
      shown_scores: FitMetrics;
      prior_model: FitMetrics;
      calibrated_model_loo: FitMetrics | null;
    } | null;
  };
  ratings: {
    student: string;
    title: string;
    completed_at: string;
    auto_score: number;
    expert_rating: number;
    expert_score: number;
    source: RatingSource;
  }[];
  plan_validation: {
    labels: Record<PlanVerdict, string>;
    clinician: PlanValidationStats;
    synthetic: PlanValidationStats;
    recent: { student: string; verdict: PlanVerdict; note: string | null; at: string; source: RatingSource; level: string }[];
  };
  assistant: { examples: number; intents: number; accuracy: number; confidence_threshold: number };
  usability: UsabilitySummary;
  adaptive: {
    students: number;
    rounds: number;
    seed: number;
    labels: Record<string, string>;
    curves: ({ round: number } & Record<string, number>)[];
    summary: {
      strategy: string;
      label: string;
      average_reward: number;
      final_10_reward: number;
      cumulative_regret: number;
      best_exercise_rate: number;
    }[];
  };
}

export interface SusStats {
  n: number;
  mean: number | null;
  sd: number | null;
  ci95: [number, number] | null;
  band: string | null;
}

export interface UsabilitySummary {
  overall: SusStats;
  by_role: { student: SusStats; therapist: SusStats };
  benchmark: number;
  items: { number: number; text: string; positive: boolean; mean_answer: number | null }[];
  comments: { role: string; score: number; comment: string; submitted_at: string }[];
}

export interface CohortReport {
  epsilon: number;
  epsilon_per_group: number;
  students: number;
  attempts_note: string;
  by_type: { label: string; value: number }[];
  levels: { label: string; value: number }[];
  mean_score: number;
  score_bands: { label: string; value: number }[];
  accuracy: { epsilon: number; count_error: number; mean_score_error: number }[];
  budget: { epsilon_spent: number; epsilon_threshold: number; epsilon_remaining: number; inference_only: boolean };
  epsilon_options: number[];
}

export interface CompareColumn {
  email: string;
  name: string;
  sessions: number;
  average_score: number | null;
  report_card: ReportCard;
  level: LevelState;
  plan: Omit<WeeklyPlanResponse, "user_id">;
  reading_speeds: { title: string; level: ReadingLevel; base_wpm: number; personal_wpm: number }[];
  assistant: AssistantReply;
}

export interface CompareResponse {
  question: string;
  students: [CompareColumn, CompareColumn];
}
