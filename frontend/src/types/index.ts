export type TaskType = "picture_description" | "video_description" | "conversation";

export type AgeCategory = "kids" | "adults";

export interface LowConfidenceSegment {
  start: number;
  end: number;
  word: string;
  confidence: number;
}

export interface AsrResult {
  transcript: string;
  average_confidence: number;
  low_confidence_segments: LowConfidenceSegment[];
}

export interface FluencyMetrics {
  words_per_minute: number;
  articulation_rate: number;
  estimated_dysfluency_density: number;
}

export interface AcousticFeatures {
  zero_crossing_rate_mean: number;
  energy_mean: number;
  tempo_bpm: number;
}

export interface AudioMetadata {
  duration_seconds: number;
  sample_rate: number;
  snr_db: number;
}

export interface ExtractFeaturesResponse {
  session_id: string;
  task_type: string;
  processing_time_seconds: number;
  audio_metadata: AudioMetadata;
  asr_result: AsrResult;
  fluency_metrics: FluencyMetrics;
  acoustic_features: AcousticFeatures;
}

export interface TaskSubmission {
  audioBlob: Blob;
  taskType: TaskType;
  sessionId: string;
  ageCategory: AgeCategory;
}
