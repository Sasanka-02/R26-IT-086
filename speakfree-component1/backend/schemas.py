"""
Pydantic request/response models.
AnalyzeResponse is the INTER-COMPONENT CONTRACT consumed by Components 2 and 3.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Role = Literal["patient", "guardian", "clinician", "admin"]
RegisterRole = Literal["patient", "guardian", "clinician"]  # "admin" cannot be self-registered
TaskType = Literal["reading", "picture", "scenario", "questions"]


# ----------------------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    role: RegisterRole
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    date_of_birth: date | None = None          # patient's own DOB (role = patient)
    child_full_name: str | None = Field(default=None, max_length=120)  # role = guardian
    child_date_of_birth: date | None = None     # role = guardian
    consent: bool

    @field_validator("consent")
    @classmethod
    def consent_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Privacy consent is required to create an account")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    date_of_birth: date


class AgeBracketOut(BaseModel):
    id: int
    label: str
    min_age: int
    max_age: int


class PatientOut(BaseModel):
    id: str
    full_name: str
    date_of_birth: date
    age: int
    age_bracket: AgeBracketOut | None
    is_self: bool


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    patients: list[PatientOut]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----------------------------------------------------------------------------- analysis contract
class TokenScoreOut(BaseModel):
    token: str
    token_id: int
    logprob: float
    probability: float


class WordSegment(BaseModel):
    index: int
    word: str
    start: float
    end: float
    duration: float
    confidence: float = Field(description="C_word – Eq. 2 (0–1)")
    confidence_percent: float
    is_dysfluency_candidate: bool
    level: Literal["high", "medium", "low"]
    whisper_word_probability: float
    tokens: list[TokenScoreOut]


class PauseOut(BaseModel):
    start: float
    end: float
    duration: float


class LowConfidenceRegion(BaseModel):
    start: float
    end: float
    words: list[str]
    min_confidence: float


class PhonemeFinding(BaseModel):
    sound: str
    accuracy_percent: float
    word_count: int
    flagged_words: list[str]
    status: Literal["ok", "warning", "flag"]


class ScreeningIndicator(BaseModel):
    severity_hint: int
    label: str
    risk: str
    note: str


class AnalyzeResponse(BaseModel):
    schema_version: str
    component: str = "C1-speech-screening"
    analysis_id: str
    session_id: str
    patient_id: str
    task_type: TaskType
    task_id: str
    age_bracket: int
    created_at: datetime
    processing_time_ms: int

    transcript: str
    reference_text: str | None

    # ---- headline biomarkers & scores ----
    overall_confidence_percent: float = Field(description="C_overall – Eq. 3")
    asr_accuracy_percent: float
    asr_score_basis: str
    fluency_score: float
    pronunciation_score: float
    articulation_score: float
    articulation_score_source: str
    overall_speech_score: float
    mean_word_confidence: float
    dysfluency_threshold: float
    dysfluency_candidate_count: int
    dysfluency_ratio: float
    word_accuracy_percent: float | None
    wer: dict | None
    content_coverage_percent: float | None

    # ---- detail ----
    word_segments: list[WordSegment]
    low_confidence_regions: list[LowConfidenceRegion]
    pauses: list[PauseOut]
    phoneme_findings: list[PhonemeFinding]
    screening_indicator: ScreeningIndicator
    acoustic_features: dict
    score_components: dict
    segments: list[dict]
    preprocessing: dict
    waveform_peaks: list[float]
    model: dict


class AnalysisSummary(BaseModel):
    analysis_id: str
    session_id: str
    task_type: str
    task_id: str
    created_at: datetime
    overall_speech_score: float
    overall_confidence_percent: float


# ----------------------------------------------------------------------------- session (all tasks) output
class FinalizeSessionRequest(BaseModel):
    patient_id: str


class SessionTaskEntry(BaseModel):
    analysis_id: str
    task_type: TaskType
    task_id: str
    title: str
    transcript: str
    overall_confidence_percent: float
    overall_speech_score: float
    asr_accuracy_percent: float
    fluency_score: float
    pronunciation_score: float
    articulation_score: float
    word_count: int
    token_count: int
    dysfluency_candidate_count: int
    dysfluency_ratio: float
    content_coverage_percent: float | None
    duration_sec: float
    words_per_minute: float
    pause_count: int
    snr_db: float
    screening_indicator: ScreeningIndicator
    created_at: datetime


class SessionSummary(BaseModel):
    """Session-level Component 1 output (pooled over every recording of the screening)."""

    schema_version: str
    component: str = "C1-speech-screening"
    summary_type: str = "session"
    session_id: str
    patient_id: str
    age_bracket: int
    created_at: datetime
    recording_count: int
    task_types: list[str]

    overall_confidence_percent: float = Field(description="Pooled C_overall – Eq. 3 over all tokens of all recordings")
    total_token_count: int
    mean_word_confidence: float
    dysfluency_threshold: float

    overall_speech_score: float
    asr_accuracy_percent: float
    fluency_score: float
    pronunciation_score: float
    articulation_score: float
    score_weighting: str
    screening_indicator: ScreeningIndicator

    word_count: int
    dysfluency_candidate_count: int
    dysfluency_ratio: float
    confidence_distribution: dict[str, int]
    lowest_confidence_words: list[dict]
    phoneme_findings: list[PhonemeFinding]

    by_task_type: dict[str, dict]
    tasks: list[SessionTaskEntry]
    acoustic_summary: dict


class SessionListItem(BaseModel):
    session_id: str
    patient_id: str
    created_at: datetime
    recording_count: int
    overall_speech_score: float
    overall_confidence_percent: float
    severity_hint: int
    label: str


# ----------------------------------------------------------------------------- clinician task library
class AdminTaskOut(BaseModel):
    id: str
    age_bracket: int
    task_type: TaskType
    title: str
    instructions: str
    content_text: str
    image_path: str | None
    image_url: str | None
    keywords: list[str]
    visual_json: dict | None
    max_seconds: int
    is_active: bool
    created_by_user_id: int | None
    created_at: datetime
    attempt_count: int


# ----------------------------------------------------------------------------- admin: patient directory
class AdminPatientRow(BaseModel):
    id: str
    full_name: str
    age: int
    age_bracket: AgeBracketOut | None
    registered_at: datetime
    owner_name: str
    owner_email: str
    owner_role: Role
    total_sessions: int
    last_session_at: datetime | None
    latest_severity_hint: int | None
    latest_label: str | None
    latest_overall_score: float | None


class AdminRecording(BaseModel):
    analysis_id: str
    task_type: TaskType
    task_id: str
    title: str
    created_at: datetime
    overall_confidence_percent: float
    overall_speech_score: float
    duration_sec: float
    audio_retained: bool = False  # raw audio is never stored on the server (privacy rule)


class AdminSessionRow(BaseModel):
    session_id: str
    created_at: datetime
    recording_count: int
    overall_speech_score: float
    overall_confidence_percent: float
    severity_hint: int
    label: str
    recordings: list[AdminRecording]


class AdminPatientProfile(BaseModel):
    patient: AdminPatientRow
    date_of_birth: date
    is_self: bool
    sessions: list[AdminSessionRow]

