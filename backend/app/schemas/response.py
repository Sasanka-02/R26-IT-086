from pydantic import BaseModel, Field


class AudioMetadata(BaseModel):
    duration_seconds: float
    sample_rate: int
    snr_db: float


class LowConfidenceSegment(BaseModel):
    start: float
    end: float
    word: str
    confidence: float


class AsrResult(BaseModel):
    transcript: str
    average_confidence: float
    low_confidence_segments: list[LowConfidenceSegment] = Field(default_factory=list)


class FluencyMetrics(BaseModel):
    words_per_minute: float
    articulation_rate: float
    estimated_dysfluency_density: float


class AcousticFeatures(BaseModel):
    zero_crossing_rate_mean: float
    energy_mean: float
    tempo_bpm: float


class ExtractFeaturesResponse(BaseModel):
    session_id: str
    task_type: str
    processing_time_seconds: float
    audio_metadata: AudioMetadata
    asr_result: AsrResult
    fluency_metrics: FluencyMetrics
    acoustic_features: AcousticFeatures


class HealthResponse(BaseModel):
    status: str
    whisper_loaded: bool
    hubert_loaded: bool
