// Shared types – mirror backend/schemas.py

export type Role = "patient" | "guardian" | "clinician" | "admin";
export type TaskType = "reading" | "picture" | "scenario" | "questions";

export interface AgeBracket {
  id: number;
  label: string;
  min_age: number;
  max_age: number;
}

export interface Patient {
  id: string;
  full_name: string;
  date_of_birth: string | null;
  age: number | null; // null -> the app asks "How old are you?" once
  age_bracket: AgeBracket | null; // clinical age bracket 1–8
  age_bracket_override?: number | null; // practice bracket pinned by a therapist
  guardian_consent?: boolean;
  is_self: boolean;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  patients: Patient[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ---------------------------------------------------------------- task engine
export type Visual =
  | { kind: "emoji"; emojis: string[]; caption: string }
  | { kind: "chart"; title: string; unit: string; data: { label: string; value: number }[] };

export interface ReadingTask {
  id: string;
  title: string;
  instructions: string;
  text: string;
  max_seconds: number;
}
export interface PictureTask {
  id: string;
  title: string;
  instructions: string;
  visual: Visual;
  image_url: string | null;
  keywords: string[];
  max_seconds: number;
}
export interface ScenarioTask {
  id: string;
  title: string;
  instructions: string;
  prompt: string;
  visual?: Visual | null;
  image_url?: string | null;
  video_url?: string | null; // short scenario video (watch, then answer)
  max_seconds: number;
}
export interface QuestionItem {
  id: string;
  prompt: string;
  max_seconds: number;
}
export interface QuestionsTask {
  id: string;
  title: string;
  instructions: string;
  items: QuestionItem[];
}
export interface TaskSet {
  patient_id: string;
  age: number;
  age_bracket: AgeBracket; // screening task bracket (1–7; adults use 7)
  therapy_bracket?: AgeBracket; // clinical age bracket (1–8)
  tasks: { reading: ReadingTask; picture: PictureTask; scenario: ScenarioTask; questions: QuestionsTask };
}

// ---------------------------------------------------------------- analysis contract
export interface TokenScore {
  token: string;
  token_id: number;
  logprob: number;
  probability: number;
}

export interface WordSegment {
  index: number;
  word: string;
  start: number;
  end: number;
  duration: number;
  confidence: number;
  confidence_percent: number;
  is_dysfluency_candidate: boolean;
  level: "high" | "medium" | "low";
  whisper_word_probability: number;
  tokens: TokenScore[];
}

export interface PhonemeFinding {
  sound: string;
  accuracy_percent: number;
  word_count: number;
  flagged_words: string[];
  status: "ok" | "warning" | "flag";
}

export interface AcousticFeatures {
  duration_sec: number;
  analysed_duration_sec: number;
  speech_duration_sec: number;
  speech_ratio: number;
  word_count: number;
  syllable_count: number;
  words_per_minute: number;
  articulation_rate_syll_per_sec: number;
  speech_rate_syll_per_sec: number;
  energy_mean_db: number;
  rmse_mean: number;
  rmse_std: number;
  zcr_mean: number;
  zcr_std: number;
  snr_db: number;
  pitch_mean_hz: number;
  pitch_std_hz: number;
  pause_count: number;
  pause_rate_per_min: number;
  mean_pause_sec: number;
  longest_pause_sec: number;
  total_pause_sec: number;
  noise_floor_db: number;
  hubert_embedding?: number[] | null;
}

export interface AnalyzeResponse {
  schema_version: string;
  component: string;
  analysis_id: string;
  session_id: string;
  patient_id: string;
  task_type: TaskType;
  task_id: string;
  age_bracket: number;
  created_at: string;
  processing_time_ms: number;
  transcript: string;
  reference_text: string | null;
  overall_confidence_percent: number;
  asr_accuracy_percent: number;
  asr_score_basis: string;
  fluency_score: number;
  pronunciation_score: number;
  articulation_score: number;
  articulation_score_source: string;
  overall_speech_score: number;
  mean_word_confidence: number;
  dysfluency_threshold: number;
  dysfluency_candidate_count: number;
  dysfluency_ratio: number;
  word_accuracy_percent: number | null;
  wer: { wer: number; substitutions: number; deletions: number; insertions: number; reference_words: number } | null;
  content_coverage_percent: number | null;
  word_segments: WordSegment[];
  low_confidence_regions: { start: number; end: number; words: string[]; min_confidence: number }[];
  pauses: { start: number; end: number; duration: number }[];
  phoneme_findings: PhonemeFinding[];
  screening_indicator: { severity_hint: number; label: string; risk: string; note: string };
  acoustic_features: AcousticFeatures;
  score_components: Record<string, unknown>;
  segments: Record<string, unknown>[];
  preprocessing: {
    sample_rate: number;
    trim_offset_sec: number;
    original_duration_sec: number;
    noise_reduction_applied: boolean;
    raw_audio_retained: boolean;
    [key: string]: unknown;
  };
  waveform_peaks: number[];
  model: {
    asr: string;
    device: string;
    token_count: number;
    verbatim_prompt: boolean;
    // schema 1.1.0: Whisper segments excluded by the hallucination guard (non-speech / repetition loops)
    rejected_segments?: { start: number; end: number; text: string; reason: string }[];
  };
}

export interface AnalysisSummary {
  analysis_id: string;
  session_id: string;
  task_type: TaskType;
  task_id: string;
  created_at: string;
  overall_speech_score: number;
  overall_confidence_percent: number;
}

// ---------------------------------------------------------------- session-level Component 1 output
export interface ScreeningIndicator {
  severity_hint: number;
  label: string;
  risk: string;
  note: string;
}

export interface SessionTaskEntry {
  analysis_id: string;
  task_type: TaskType;
  task_id: string;
  title: string;
  transcript: string;
  overall_confidence_percent: number;
  overall_speech_score: number;
  asr_accuracy_percent: number;
  fluency_score: number;
  pronunciation_score: number;
  articulation_score: number;
  word_count: number;
  token_count: number;
  dysfluency_candidate_count: number;
  dysfluency_ratio: number;
  content_coverage_percent: number | null;
  duration_sec: number;
  words_per_minute: number;
  pause_count: number;
  snr_db: number;
  screening_indicator: ScreeningIndicator;
  created_at: string;
}

export interface SessionSummary {
  schema_version: string;
  component: string;
  summary_type: "session";
  session_id: string;
  patient_id: string;
  age_bracket: number;
  created_at: string;
  recording_count: number;
  task_types: TaskType[];
  overall_confidence_percent: number;
  total_token_count: number;
  mean_word_confidence: number;
  dysfluency_threshold: number;
  overall_speech_score: number;
  asr_accuracy_percent: number;
  fluency_score: number;
  pronunciation_score: number;
  articulation_score: number;
  score_weighting: string;
  screening_indicator: ScreeningIndicator;
  word_count: number;
  dysfluency_candidate_count: number;
  dysfluency_ratio: number;
  confidence_distribution: { high: number; medium: number; low: number };
  lowest_confidence_words: {
    word: string;
    confidence: number;
    task_type: TaskType;
    task_id: string;
    analysis_id: string;
    start: number;
    is_dysfluency_candidate: boolean;
  }[];
  phoneme_findings: PhonemeFinding[];
  by_task_type: Partial<Record<TaskType, {
    recordings: number;
    overall_confidence_percent: number;
    overall_speech_score: number;
    word_count: number;
    token_count: number;
    dysfluency_candidate_count: number;
  }>>;
  tasks: SessionTaskEntry[];
  acoustic_summary: {
    total_duration_sec: number;
    total_speech_sec: number;
    words_per_minute: number;
    articulation_rate_syll_per_sec: number;
    energy_mean_db: number;
    rmse_mean: number;
    zcr_mean: number;
    snr_db: number;
    min_snr_db: number;
    pitch_mean_hz: number;
    speech_ratio: number;
    pause_count: number;
    pause_rate_per_min: number;
    longest_pause_sec: number;
    total_pause_sec: number;
  };
}

export interface SessionListItem {
  session_id: string;
  patient_id: string;
  created_at: string;
  recording_count: number;
  overall_speech_score: number;
  overall_confidence_percent: number;
  severity_hint: number;
  label: string;
}

export const TASK_LABEL: Record<TaskType, string> = {
  reading: "Audio Recording",
  picture: "Picture Description",
  scenario: "Scenario Description",
  questions: "Pre-defined Questions",
};

// ---------------------------------------------------------------- clinician task library
export interface AdminTask {
  id: string;
  age_bracket: number;
  task_type: TaskType;
  title: string;
  instructions: string;
  content_text: string;
  image_path: string | null; // picture, or a short video for scenario tasks
  image_url: string | null;
  video_url?: string | null;
  keywords: string[];
  visual_json: Visual | null;
  max_seconds: number;
  is_active: boolean;
  created_by_user_id: number | null;
  created_at: string;
  attempt_count: number;
}

// ---------------------------------------------------------------- admin: patient directory & history
export interface AdminPatientRow {
  id: string;
  full_name: string;
  age: number | null;
  age_bracket: AgeBracket | null;
  age_bracket_override?: number | null;
  registered_at: string;
  owner_name: string;
  owner_email: string;
  owner_role: Role;
  total_sessions: number;
  last_session_at: string | null;
  latest_severity_hint: number | null;
  latest_label: string | null;
  latest_overall_score: number | null;
}

export interface AdminRecording {
  analysis_id: string;
  task_type: TaskType;
  task_id: string;
  title: string;
  created_at: string;
  overall_confidence_percent: number;
  overall_speech_score: number;
  duration_sec: number;
  audio_retained: boolean;
}

export interface AdminSessionRow {
  session_id: string;
  created_at: string;
  recording_count: number;
  overall_speech_score: number;
  overall_confidence_percent: number;
  severity_hint: number;
  label: string;
  recordings: AdminRecording[];
}

export interface AdminPatientProfile {
  patient: AdminPatientRow;
  date_of_birth: string | null;
  is_self: boolean;
  sessions: AdminSessionRow[];
}

