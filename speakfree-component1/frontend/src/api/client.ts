// Thin fetch wrapper around the Component 1 FastAPI backend.
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
  date_of_birth?: string | null;
  child_full_name?: string | null;
  child_date_of_birth?: string | null;
  consent: boolean;
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

export const api = {
  register: (data: RegisterPayload) => request<TokenResponse>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/api/v1/auth/me"),
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
