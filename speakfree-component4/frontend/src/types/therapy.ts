export type ExerciseType = "pacing" | "daf" | "picture" | "reading";
export type SeverityLevel = "mild" | "moderate" | "severe" | "unknown";

/** Severity received from the screening components (1–3). */
export interface Screening {
  severity: SeverityLevel;
  source: string;
  by: string;
  at: string;
}
export type ReadingLevel = "beginner" | "intermediate" | "advanced";
export type SelfRating = "easy" | "ok" | "hard";

export interface TherapyExercise {
  id: string;
  type: ExerciseType;
  title: string;
  description: string;
  target_wpm: number | null;
  passage: string | null;
  image_url: string | null;
  prompts: string[];
  example_sentences: string[];
  level: ReadingLevel | null;
  difficulty: number;
  recommended_for: SeverityLevel[];
  locked?: boolean;
  assigned?: boolean;
  base_wpm?: number;
}

export interface FeedbackMessage {
  type: string;
  message: string;
  severity: "info" | "warning" | "success";
}

export interface LiveMetric {
  timestamp_ms: number;
  rms_energy: number;
  zero_crossing_rate: number;
  is_speaking: boolean;
  syllables: number;
}

export interface DafTrial {
  delay_ms: number;
  stutter_events: number;
  speech_rate_wpm: number;
}

export interface LevelState {
  level: ReadingLevel;
  level_index: number;
  label: string;
  next_level: ReadingLevel | null;
  next_label: string | null;
  strong_in_a_row: number;
  needed_to_advance: number;
  mastered: boolean;
  progress_text: string;
  set_by_therapist: boolean;
  strong_threshold: number;
  weak_threshold: number;
  history: LevelEvent[];
}

/** One move on the reading-level ladder, replayed from the student's own attempts. */
export interface LevelEvent {
  at: string;
  from: string | null;
  to: string;
  direction: "up" | "down" | "mastered" | "therapist";
  reason: string;
}

export type ReportStatus = "improving" | "steady" | "needs_support";

/** Plain-language summary shown before any chart. */
export interface ReportCard {
  status: ReportStatus;
  label: string;
  headline: string;
  this_week: string;
  next_step: string;
  reasons: string[];
}

export interface UserExercisesResponse {
  level: LevelState;
  exercises: TherapyExercise[];
}

export interface ExerciseResultInput {
  exercise_id: string;
  duration_seconds: number;
  speaking_ratio?: number | null;
  long_pauses?: number;
  quiet_warnings?: number;
  syllables?: number | null;
  target_wpm?: number | null;
  self_rating: SelfRating;
}

export interface PracticeRecord {
  id: string;
  exercise_id: string;
  exercise_type: ExerciseType;
  title: string;
  level: ReadingLevel | null;
  completed_at: string;
  duration_seconds: number;
  score: number;
  self_rating: SelfRating;
}

export interface ExerciseResultResponse {
  record: PracticeRecord;
  score: number;
  verdict: string;
  feedback: string[];
  level: LevelState;
  level_message: string | null;
  breakdown: ScorePart[];
  measured_wpm: number | null;
  target_wpm: number | null;
}

export interface ScorePart {
  feature: string;
  label: string;
  value: number;
  weight: number;
  points: number;
}

export interface Badge {
  id: string;
  title: string;
  description: string;
  earned: boolean;
}

export type GoalMetric = "average_score" | "sessions_per_week" | "long_pauses_per_reading";

export interface GoalProgress {
  id: string;
  metric: GoalMetric;
  target: number;
  label: string;
  text: string;
  current: number | null;
  met: boolean;
}

export interface FirstVsLatest {
  exercise_id: string;
  title: string;
  attempts: number;
  first_score: number;
  latest_score: number;
  change: number;
  first_pauses: number | null;
  latest_pauses: number | null;
}

export interface ProgressSummary {
  user_id: string;
  has_data: boolean;
  level: LevelState;
  total_sessions: number;
  total_minutes: number;
  active_days: number;
  streak_days: number;
  average_score: number | null;
  best_score: number | null;
  trend: { label: string; detail: string };
  by_type: {
    type: ExerciseType;
    label: string;
    sessions: number;
    average_score: number | null;
    best_score: number;
    last_done: string;
  }[];
  weekly: { label: string; sessions: number; minutes: number; average_score: number | null }[];
  daily: { date: string; sessions: number; average_score: number | null }[];
  history: {
    attempt: number;
    completed_at: string;
    score: number;
    title: string;
    exercise_type: ExerciseType;
  }[];
  recent: {
    id: string;
    title: string;
    exercise_type: ExerciseType;
    completed_at: string;
    score: number;
    verdict: string;
    self_rating: SelfRating;
    duration_seconds: number;
  }[];
  highlights: string[];
  badges: Badge[];
  goals: GoalProgress[];
  first_vs_latest: FirstVsLatest[];
  report_card: ReportCard;
}

export interface PlanExercise {
  id: string;
  title: string;
  type: ExerciseType;
  difficulty: number;
  reason: string;
  source: "therapist" | "level" | "bandit";
  times_practised: number;
  predicted_score: number | null;
  uncertainty: number | null;
  /** The bandit's numbers for this exercise, in words. */
  explanation: string;
  rank?: number;
  compared?: number;
}

export interface WeeklyPlanResponse {
  user_id: string;
  level: LevelState;
  exercises: PlanExercise[];
  screening: Screening | null;
  /** The context the plan was built from, in words. */
  why: string[];
  context: { level: number; recent_average: number; trend: number; comfort: number };
}

export interface AssistantAction {
  exercise_id: string;
  label: string;
}

export interface AssistantBriefing {
  greeting: string;
  summary: string[];
  focus: { title: string; tip: string };
  next_step: { exercise_id: string; title: string; reason: string };
  goals: GoalProgress[];
  badges_earned: number;
  badges_total: number;
  suggestions: string[];
  llm_enabled: boolean;
}

export interface AssistantReply {
  reply: string;
  action: AssistantAction | null;
  suggestions: string[];
  intent: string | null;
  confidence: number;
  source: "classifier" | "llm" | "fallback";
}

export interface SessionSummary {
  session_id: string;
  duration_seconds: number;
  speaking_ratio: number;
  pause_count: number;
  quiet_warnings: number;
  syllables: number;
}

export interface PrivacyBudget {
  patient_id: string;
  epsilon_spent: number;
  epsilon_threshold: number;
  epsilon_remaining: number;
  inference_only: boolean;
}
