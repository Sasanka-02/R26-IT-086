import { api } from "../api/client";
import { ReadingLevel } from "../types/therapy";
import {
  CaseloadOverview,
  CohortReport,
  CompareResponse,
  EvidenceReport,
  GoalMetric,
  PlanReview,
  PlanVerdict,
  StudentDetail,
  StudentRow,
} from "../types/therapist";

const student = (email: string) => `/api/v1/therapist/students/${encodeURIComponent(email)}`;

export async function getCaseloadOverview(): Promise<CaseloadOverview> {
  return (await api.get("/api/v1/therapist/overview")).data;
}

export async function getStudents(): Promise<StudentRow[]> {
  return (await api.get("/api/v1/therapist/students")).data;
}

export async function getStudentDetail(email: string): Promise<StudentDetail> {
  return (await api.get(student(email))).data;
}

export async function setAssignedExercises(email: string, exerciseIds: string[]) {
  return (await api.put(`${student(email)}/assigned`, { exercise_ids: exerciseIds })).data;
}

export async function setLevelOverride(email: string, level: ReadingLevel | null) {
  return (await api.put(`${student(email)}/level`, { level })).data;
}

export async function addGoal(email: string, metric: GoalMetric, target: number) {
  return (await api.post(`${student(email)}/goals`, { metric, target })).data;
}

export async function removeGoal(email: string, goalId: string) {
  return (await api.delete(`${student(email)}/goals/${goalId}`)).data;
}

export async function addNote(email: string, text: string) {
  return (await api.post(`${student(email)}/notes`, { text })).data;
}

export async function rateAttempt(email: string, recordId: string, rating: number) {
  return (await api.put(`${student(email)}/records/${recordId}/rating`, { rating })).data;
}

export async function getEvidence(): Promise<EvidenceReport> {
  return (await api.get("/api/v1/therapist/evidence")).data;
}

export async function getCohortReport(epsilon: number): Promise<CohortReport> {
  return (await api.get("/api/v1/therapist/cohort-report", { params: { epsilon } })).data;
}

export async function reviewPlan(email: string, verdict: PlanVerdict, note?: string): Promise<PlanReview> {
  return (await api.post(`${student(email)}/plan-review`, { verdict, note })).data;
}

export async function compareStudents(a: string, b: string): Promise<CompareResponse> {
  return (await api.get("/api/v1/therapist/compare", { params: { a, b } })).data;
}

/** Saves every expert rating as a CSV file (the rating sheet for the report). */
export async function downloadRatingsSheet() {
  const res = await api.get("/api/v1/therapist/evidence/ratings.csv", { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "expert-ratings.csv";
  link.click();
  URL.revokeObjectURL(url);
}
