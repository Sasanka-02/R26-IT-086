from enum import Enum

from pydantic import BaseModel, Field


class ExerciseType(str, Enum):
    PACING = "pacing"
    DAF = "daf"
    PICTURE = "picture"
    READING = "reading"


class ReadingLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SelfRating(str, Enum):
    EASY = "easy"
    OK = "ok"
    HARD = "hard"


class SeverityLevel(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class TherapyExercise(BaseModel):
    id: str
    type: ExerciseType
    title: str
    description: str
    target_wpm: int | None = None
    passage: str | None = None
    image_url: str | None = None
    prompts: list[str] = Field(default_factory=list)
    example_sentences: list[str] = Field(default_factory=list)  # model answer for picture tasks
    level: ReadingLevel | None = None
    difficulty: int = 1
    recommended_for: list[SeverityLevel] = Field(default_factory=list)


class ScreeningRequest(BaseModel):
    """Severity from the screening components (1–3) for one student."""
    user_id: str
    severity: SeverityLevel
    source: str = Field(default="Component 1 screening", max_length=80)


class StartSessionRequest(BaseModel):
    session_id: str
    severity: SeverityLevel = SeverityLevel.UNKNOWN


class StartSessionResponse(BaseModel):
    session_id: str
    recommended_exercises: list[TherapyExercise]


class LiveMetric(BaseModel):
    timestamp_ms: float
    rms_energy: float
    zero_crossing_rate: float
    is_speaking: bool
    syllables: int = 0  # syllable-like energy peaks detected in the browser this interval


class FeedbackMessage(BaseModel):
    type: str
    message: str
    severity: str = "info"


class EndSessionRequest(BaseModel):
    session_id: str


class SessionSummary(BaseModel):
    session_id: str
    duration_seconds: float
    exercise_type: ExerciseType | None
    speaking_ratio: float
    avg_energy: float
    pause_count: int
    feedback_events: int
    quiet_warnings: int = 0
    syllables: int = 0


class DafCalibrationTrial(BaseModel):
    delay_ms: int
    stutter_events: int
    speech_rate_wpm: float


class DafCalibrationRequest(BaseModel):
    session_id: str
    trials: list[DafCalibrationTrial]


class DafCalibrationResult(BaseModel):
    session_id: str
    recommended_delay_ms: int
    trials_evaluated: int


class BiomarkerCompareRequest(BaseModel):
    task_type: str
    patient_metrics: dict


class PrivacyBudgetResponse(BaseModel):
    patient_id: str
    epsilon_spent: float
    epsilon_threshold: float
    epsilon_remaining: float
    inference_only: bool


class ExerciseResultRequest(BaseModel):
    user_id: str
    exercise_id: str
    duration_seconds: float = 0
    speaking_ratio: float | None = None
    long_pauses: int = 0
    quiet_warnings: int = 0
    syllables: int | None = None
    target_wpm: int | None = None
    self_rating: SelfRating = SelfRating.OK
    # Optional, from a teammate's ASR / disfluency detector (Components 1–3):
    # repetitions + prolongations + blocks counted in this attempt. With
    # `syllables` it gives %SS, the standard clinical stuttering measure.
    disfluencies: int | None = Field(default=None, ge=0)


class AssistantChatRequest(BaseModel):
    user_id: str
    name: str = ""
    message: str
