// Thin fetch wrapper around the Component 1 FastAPI backend.
import type {
  AdminTherapy, AttemptPayload, AttemptResult, Briefing, ChatReply, CohortReport, DafTrial, Evidence, ModelsInfo, PipelineDetail,
  PipelineOverview, PlanResponse, PrivacyInfo, SurveyStatus, TherapyNote,
} from "../types/integration";
import type { AdminPatientProfile, AdminPatientRow, AdminTask, AnalysisSummary, AnalyzeResponse, Patient, Role, SessionListItem, SessionSummary, TaskSet, TokenResponse, User } from "../types";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "speakfree.token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable – token lives only in memory for this tab */
    }
  },
};

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // FastAPI validation errors: [{loc, msg, ...}]
      return detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg).replace(/^Value error, /, "") : String(d)))
        .join(". ");
    }
  }
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, `Cannot reach the SpeakFree server at ${API_BASE}. Is the backend running?`);
  }

  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) throw new ApiError(res.status, errorMessage(body, `Request failed (${res.status})`));
  return body as T;
}

export interface RegisterPayload {
  role: Role;
  full_name: string;
  email: string;
  password: string;
  age?: number | null; // role = patient (6–100)
  date_of_birth?: string | null;
  child_full_name?: string | null;
  child_age?: number | null; // role = guardian
  child_date_of_birth?: string | null;
  guardian_consent?: boolean; // required when the person practising is under 18
  consent: boolean;
}

export interface TherapistSettings {
  age_bracket_override?: number | null;
  assigned_exercise_ids?: string[];
}

export interface AnalyzePayload {
  audio: Blob;
  filename: string;
  sessionId: string;
  patientId: string;
  ageBracket: number;
  taskType: string;
  taskId: string;
}

export interface Appointment {
  id: number;
  patient_id: string;
  patient_name: string;
  preferred_date: string;
  preferred_time: "morning" | "afternoon" | "evening";
  mode: "online" | "in_person";
  reason: string;
  status: "pending" | "confirmed" | "declined" | "cancelled";
  admin_note: string | null;
  scheduled_at: string | null;
  created_at: string;
  requested_by?: string;
  requested_by_email?: string;
  requested_by_role?: string;
}

export const api = {
  register: (data: RegisterPayload) => request<TokenResponse>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/api/v1/auth/me"),
  setMyAge: (age: number, guardian_consent: boolean, patient_id?: string) =>
    request<User>("/api/v1/auth/me/age", { method: "PUT", body: JSON.stringify({ age, guardian_consent, patient_id }) }),
  updateMe: (full_name: string) => request<{ full_name: string }>("/api/v1/auth/me", { method: "PATCH", body: JSON.stringify({ full_name }) }),
  changePassword: (current_password: string, new_password: string) =>
    request<null>("/api/v1/auth/change-password", { method: "POST", body: JSON.stringify({ current_password, new_password }) }),
  appointments: {
    mine: () => request<Appointment[]>("/api/v1/appointments"),
    create: (body: Omit<Appointment, "id" | "patient_name" | "status" | "admin_note" | "scheduled_at" | "created_at">) =>
      request<Appointment>("/api/v1/appointments", { method: "POST", body: JSON.stringify(body) }),
    cancel: (id: number) => request<Appointment>(`/api/v1/appointments/${id}/cancel`, { method: "POST" }),
    all: (status?: string) => request<Appointment[]>(`/api/v1/admin/appointments${status ? `?status=${status}` : ""}`),
    decide: (id: number, body: { status: "confirmed" | "declined"; scheduled_at?: string; admin_note?: string }) =>
      request<Appointment>(`/api/v1/admin/appointments/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  },
  createPatient: (full_name: string, date_of_birth: string) =>
    request<Patient>("/api/v1/patients", { method: "POST", body: JSON.stringify({ full_name, date_of_birth }) }),
  tasks: (patientId: string) => request<TaskSet>(`/api/v1/tasks?patient_id=${encodeURIComponent(patientId)}`),
  analyze: (p: AnalyzePayload) => {
    const form = new FormData();
    form.append("audio", p.audio, p.filename);
    form.append("session_id", p.sessionId);
    form.append("patient_id", p.patientId);
    form.append("age_bracket", String(p.ageBracket));
    form.append("task_type", p.taskType);
    form.append("task_id", p.taskId);
    return request<AnalyzeResponse>("/api/v1/analyze", { method: "POST", body: form });
  },
  result: (analysisId: string) => request<AnalyzeResponse>(`/api/v1/results/${encodeURIComponent(analysisId)}`),
  history: (patientId: string) => request<AnalysisSummary[]>(`/api/v1/patients/${encodeURIComponent(patientId)}/history`),
  finalizeSession: (sessionId: string, patientId: string) =>
    request<SessionSummary>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/finalize`, {
      method: "POST",
      body: JSON.stringify({ patient_id: patientId }),
    }),
  sessionSummary: (sessionId: string) => request<SessionSummary>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/summary`),
  sessions: (patientId: string) => request<SessionListItem[]>(`/api/v1/patients/${encodeURIComponent(patientId)}/sessions`),
  warmup: () => request<{ whisper_loaded: boolean }>("/api/v1/system/warmup", { method: "POST" }),
  // admin-only: patient directory, profiles and session history
  admin: {
    patients: () => request<AdminPatientRow[]>("/api/v1/admin/patients"),
    patient: (id: string) => request<AdminPatientProfile>(`/api/v1/admin/patients/${encodeURIComponent(id)}`),
    // integrated pipeline (Components 2–4) – admin only
    pipeline: () => request<PipelineOverview>("/api/v1/admin/pipeline"),
    pipelineRun: (sessionId: string) => request<PipelineDetail>(`/api/v1/admin/pipeline/${encodeURIComponent(sessionId)}`),
    rerunPipeline: (sessionId: string) =>
      request<{ status: string; error: string | null }>(`/api/v1/admin/pipeline/${encodeURIComponent(sessionId)}/rerun`, { method: "POST" }),
    models: () => request<ModelsInfo>("/api/v1/admin/models"),
    therapy: (patientId: string) => request<AdminTherapy>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/therapy`),
    therapySettings: (patientId: string, body: TherapistSettings) =>
      request<AdminTherapy["patient"]>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/therapy-settings`,
        { method: "PATCH", body: JSON.stringify(body) }),
    // therapist controls (Component 4)
    addGoal: (patientId: string, metric: string, target: number) =>
      request<unknown>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/goals`, { method: "POST", body: JSON.stringify({ metric, target }) }),
    removeGoal: (patientId: string, goalId: number) =>
      request<null>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/goals/${goalId}`, { method: "DELETE" }),
    addNote: (patientId: string, text: string, shared: boolean) =>
      request<TherapyNote>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/notes`, { method: "POST", body: JSON.stringify({ text, shared }) }),
    setHomework: (patientId: string, exerciseId: string, body: { due: string | null; times: number }) =>
      request<unknown>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/homework/${encodeURIComponent(exerciseId)}`,
        { method: "PATCH", body: JSON.stringify(body) }),
    rateAttempt: (attemptId: number, rating: number, note?: string) =>
      request<unknown>(`/api/v1/admin/attempts/${attemptId}/rating`, { method: "PUT", body: JSON.stringify({ rating, note }) }),
    reviewPlan: (patientId: string, verdict: string, note?: string) =>
      request<unknown>(`/api/v1/admin/patients/${encodeURIComponent(patientId)}/plan-review`, { method: "POST", body: JSON.stringify({ verdict, note }) }),
    evidence: () => request<Evidence>("/api/v1/admin/evidence"),
    cohort: (epsilon: number) => request<CohortReport>(`/api/v1/admin/evidence/cohort?epsilon=${epsilon}`),
  },
  survey: {
    status: () => request<SurveyStatus>("/api/v1/survey"),
    submit: (answers: number[], comment?: string) =>
      request<{ score: number; band: string }>("/api/v1/survey", { method: "POST", body: JSON.stringify({ answers, comment }) }),
  },
  // Component 4 – patient-safe therapy plan, exercises and AI assistant
  therapy: {
    plan: (patientId: string) => request<PlanResponse>(`/api/v1/therapy/${encodeURIComponent(patientId)}/plan`),
    submit: (patientId: string, body: AttemptPayload) =>
      request<AttemptResult>(`/api/v1/therapy/${encodeURIComponent(patientId)}/attempts`, { method: "POST", body: JSON.stringify(body) }),
    briefing: (patientId: string) => request<Briefing>(`/api/v1/therapy/${encodeURIComponent(patientId)}/assistant`),
    chat: (patientId: string, message: string) =>
      request<ChatReply>(`/api/v1/therapy/${encodeURIComponent(patientId)}/assistant/chat`, { method: "POST", body: JSON.stringify({ message }) }),
    notes: (patientId: string) => request<{ notes: TherapyNote[]; unread: number }>(`/api/v1/therapy/${encodeURIComponent(patientId)}/notes`),
    readNotes: (patientId: string) =>
      request<{ notes: TherapyNote[]; unread: number }>(`/api/v1/therapy/${encodeURIComponent(patientId)}/notes/read`, { method: "POST" }),
    calibrateDaf: (patientId: string, trials: DafTrial[]) =>
      request<{ recommended_delay_ms: number; trials_evaluated: number }>(`/api/v1/therapy/${encodeURIComponent(patientId)}/daf/calibrate`,
        { method: "POST", body: JSON.stringify({ trials }) }),
    privacy: (patientId: string) => request<PrivacyInfo>(`/api/v1/therapy/${encodeURIComponent(patientId)}/privacy`),
    exportData: (patientId: string) => request<unknown>(`/api/v1/therapy/${encodeURIComponent(patientId)}/export`),
    liveUrl: (liveId: string, exerciseType: string) =>
      `${API_BASE.replace(/^http/, "ws")}/ws/therapy-live/${encodeURIComponent(liveId)}?token=${encodeURIComponent(tokenStore.get() ?? "")}&exercise_type=${encodeURIComponent(exerciseType)}`,
  },
  // clinician-only task library (multipart so an image can be uploaded with the fields)
  adminTasks: {
    list: (filters: { ageBracket?: number; taskType?: string } = {}) => {
      const q = new URLSearchParams();
      if (filters.ageBracket) q.set("age_bracket", String(filters.ageBracket));
      if (filters.taskType) q.set("task_type", filters.taskType);
      return request<AdminTask[]>(`/api/v1/admin/tasks?${q.toString()}`);
    },
    create: (form: FormData) => request<AdminTask>("/api/v1/admin/tasks", { method: "POST", body: form }),
    update: (id: string, form: FormData) =>
      request<AdminTask>(`/api/v1/admin/tasks/${encodeURIComponent(id)}`, { method: "PATCH", body: form }),
  },
};

// Local audio blobs (never re-uploaded) so the dashboard can play/scrub the user's own recording.
const audioUrls = new Map<string, string>();
export const localAudio = {
  set(analysisId: string, blob: Blob) {
    audioUrls.set(analysisId, URL.createObjectURL(blob));
  },
  get(analysisId: string): string | undefined {
    return audioUrls.get(analysisId);
  },
};
