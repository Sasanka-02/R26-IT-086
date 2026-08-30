export type ExerciseType = "pacing" | "daf" | "picture";
export type SeverityLevel = "mild" | "moderate" | "severe" | "unknown";

export interface TherapyExercise {
  id: string;
  type: ExerciseType;
  title: string;
  description: string;
  target_wpm: number | null;
  passage: string | null;
  image_url: string | null;
  recommended_for: SeverityLevel[];
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
}

export interface DafTrial {
  delay_ms: number;
  stutter_events: number;
  speech_rate_wpm: number;
}

export interface DashboardWeek {
  week: number;
  stuttering_events_per_min: number;
  articulation_accuracy: number;
  speech_rate_wpm: number;
  sessions_completed: number;
}

export interface DashboardResponse {
  session_id: string;
  weekly_trend: DashboardWeek[];
  total_practice_sessions: number;
  current_streak_weeks: number;
  total_practice_hours: number;
}

export interface PlanExercise {
  id: string;
  title: string;
  difficulty: number;
}

export interface PrivacyBudget {
  patient_id: string;
  epsilon_spent: number;
  epsilon_threshold: number;
  epsilon_remaining: number;
  inference_only: boolean;
}
