from enum import Enum

from pydantic import BaseModel, Field


class ExerciseType(str, Enum):
    PACING = "pacing"
    DAF = "daf"
    PICTURE = "picture"


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
    recommended_for: list[SeverityLevel] = Field(default_factory=list)


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


class WeeklyPlanRequest(BaseModel):
    session_id: str
    severity_level: int = 2
    avg_stutter_freq: float = 5.0
    trend: float = 0.0
    comfort_score: float = 0.5


class WeeklyPlanExercise(BaseModel):
    id: str
    title: str
    difficulty: int


class WeeklyPlanResponse(BaseModel):
    session_id: str
    exercises: list[WeeklyPlanExercise]


class BiomarkerCompareRequest(BaseModel):
    task_type: str
    patient_metrics: dict


class PrivacyBudgetResponse(BaseModel):
    patient_id: str
    epsilon_spent: float
    epsilon_threshold: float
    epsilon_remaining: float
    inference_only: bool
