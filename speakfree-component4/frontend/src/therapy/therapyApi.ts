import { api as client, API_BASE_URL } from "../api/client";
import {
  AssistantBriefing,
  AssistantReply,
  DafTrial,
  ExerciseResultInput,
  ExerciseResultResponse,
  PrivacyBudget,
  ProgressSummary,
  SessionSummary,
  SeverityLevel,
  TherapyExercise,
  UserExercisesResponse,
  WeeklyPlanResponse,
} from "../types/therapy";

const user = (userId: string) => encodeURIComponent(userId);

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

export async function endTherapySession(sessionId: string): Promise<SessionSummary> {
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

export async function getUserExercises(userId: string): Promise<UserExercisesResponse> {
  const res = await client.get(`/api/v1/therapy/exercises/user/${user(userId)}`);
  return res.data;
}

export async function submitResult(
  userId: string,
  result: ExerciseResultInput
): Promise<ExerciseResultResponse> {
  const res = await client.post("/api/v1/therapy/results", { user_id: userId, ...result });
  return res.data;
}

export async function getProgress(userId: string): Promise<ProgressSummary> {
  const res = await client.get(`/api/v1/therapy/progress/${user(userId)}`);
  return res.data;
}

export async function getWeeklyPlan(userId: string): Promise<WeeklyPlanResponse> {
  const res = await client.get(`/api/v1/therapy/plan/${user(userId)}`);
  return res.data;
}

export async function getAssistantBriefing(
  userId: string,
  name: string
): Promise<AssistantBriefing> {
  const res = await client.get(`/api/v1/therapy/assistant/${user(userId)}`, {
    params: { name },
  });
  return res.data;
}

export async function askAssistant(
  userId: string,
  name: string,
  message: string
): Promise<AssistantReply> {
  const res = await client.post("/api/v1/therapy/assistant/chat", {
    user_id: userId,
    name,
    message,
  });
  return res.data;
}

export async function getPrivacyBudget(userId: string): Promise<PrivacyBudget> {
  const res = await client.get(`/api/v1/therapy/privacy/budget/${user(userId)}`);
  return res.data;
}

export async function getFederatedArchitecture() {
  const res = await client.get("/api/v1/therapy/federated/architecture");
  return res.data;
}

/** Screening result from Components 1–3: sets the starting level and steers the plan. */
export async function submitScreening(userId: string, severity: SeverityLevel, source = "Component 1 screening") {
  return (await client.post("/api/v1/therapy/screening", { user_id: userId, severity, source })).data;
}

/** Downloads everything stored about the logged-in account as a JSON file. */
export async function downloadMyData() {
  const res = await client.get("/api/v1/auth/me/data", { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "speakfree-my-data.json";
  link.click();
  URL.revokeObjectURL(url);
}

export async function deleteMyAccount() {
  return (await client.delete("/api/v1/auth/me")).data;
}
