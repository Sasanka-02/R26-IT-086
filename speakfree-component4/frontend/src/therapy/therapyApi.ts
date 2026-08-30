import axios from "axios";
import {
  DafTrial,
  DashboardResponse,
  PlanExercise,
  PrivacyBudget,
  SeverityLevel,
  TherapyExercise,
} from "../types/therapy";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;
const client = axios.create({ baseURL: API_BASE_URL });

export async function startTherapySession(
  sessionId: string,
  severity: SeverityLevel = "unknown"
): Promise<TherapyExercise[]> {
  const res = await client.post("/api/v1/therapy/session/start", {
    session_id: sessionId,
    severity,
  });
  return res.data.recommended_exercises;
}

export async function endTherapySession(sessionId: string) {
  const res = await client.post("/api/v1/therapy/session/end", {
    session_id: sessionId,
  });
  return res.data;
}

export function buildTherapyWsUrl(sessionId: string, exerciseType: string): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/api/v1/therapy/ws/${sessionId}?exercise_type=${exerciseType}`;
}

export async function calibrateDaf(sessionId: string, trials: DafTrial[]) {
  const res = await client.post("/api/v1/therapy/daf/calibrate", {
    session_id: sessionId,
    trials,
  });
  return res.data as { recommended_delay_ms: number; trials_evaluated: number };
}

export async function getDashboard(sessionId: string): Promise<DashboardResponse> {
  const res = await client.get(`/api/v1/therapy/dashboard/${sessionId}`);
  return res.data;
}

export async function getWeeklyPlan(
  sessionId: string,
  severityLevel = 2,
  avgStutterFreq = 5.0,
  trend = 0.0,
  comfortScore = 0.5
): Promise<PlanExercise[]> {
  const res = await client.post("/api/v1/therapy/plan/weekly", {
    session_id: sessionId,
    severity_level: severityLevel,
    avg_stutter_freq: avgStutterFreq,
    trend,
    comfort_score: comfortScore,
  });
  return res.data.exercises;
}

export async function getPrivacyBudget(sessionId: string): Promise<PrivacyBudget> {
  const res = await client.get(`/api/v1/therapy/privacy/budget/${sessionId}`);
  return res.data;
}

export async function getFederatedArchitecture() {
  const res = await client.get("/api/v1/therapy/federated/architecture");
  return res.data;
}
