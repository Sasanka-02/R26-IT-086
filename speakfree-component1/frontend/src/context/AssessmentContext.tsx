/**
 * AssessmentContext – holds the current screening session for the active patient.
 *
 * Recordings are kept as Blobs as the patient moves through the task pages and are only uploaded
 * when "Analyse Now" is pressed. They are mirrored to IndexedDB (utils/recordingStore) so a page
 * reload does not lose them, and deleted from the browser once the analysis has completed. Each
 * recording remembers its analysis_id once analysed, so a failed batch can be retried without
 * re-sending the recordings that succeeded.
 *
 * The task set (served from the database, rotating per patient) is stored WITH the session: once
 * something is recorded, the patient keeps the same tasks until the session is analysed (or they
 * press "Start over"), and a fresh set is fetched for the next session. A saved session with no
 * recordings yet always fetches the current tasks, so new pictures / videos from the Task Library
 * show up immediately.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { recordingStore } from "../utils/recordingStore";
import type { TaskSet, TaskType } from "../types";
import { useAuth } from "./AuthContext";

export interface Recording {
  key: string; // "picture" | "scenario" | question item id
  taskType: TaskType;
  taskId: string;
  blob: Blob;
  filename: string;
  durationSec: number;
  analysisId?: string;
}

interface SessionState {
  sessionId: string;
  recordings: Record<string, Recording>;
  taskSet?: TaskSet; // snapshot of the tasks this session is using
}

/** One entry per recording the session needs, in the order they are analysed. */
export interface RequiredItem {
  key: string;
  taskType: TaskType;
  taskId: string;
  label: string;
}

interface AssessmentState {
  taskSet: TaskSet | null;
  taskError: string | null;
  session: SessionState | null;
  required: RequiredItem[];
  completedCount: number;
  allRecorded: boolean;
  saveRecording: (rec: Omit<Recording, "analysisId">) => void;
  removeRecording: (key: string) => void;
  markAnalysed: (key: string, analysisId: string) => void;
  resetSession: () => void;
}

const Ctx = createContext<AssessmentState | null>(null);

function newSession(): SessionState {
  return { sessionId: crypto.randomUUID(), recordings: {} };
}

export function requiredItems(taskSet: TaskSet): RequiredItem[] {
  const { picture, scenario, questions } = taskSet.tasks;
  return [
    { key: "picture", taskType: "picture", taskId: picture.id, label: `Picture Description – ${picture.title}` },
    { key: "scenario", taskType: "scenario", taskId: scenario.id, label: `Scenario Description – ${scenario.title}` },
    ...questions.items.map((q, i) => ({ key: q.id, taskType: "questions" as const, taskId: q.id, label: `Question ${i + 1} – ${q.prompt}` })),
  ];
}

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const { activePatient } = useAuth();
  const patientId = activePatient?.id ?? null;
  const [sessions, setSessions] = useState<Record<string, SessionState>>({});
  const [taskError, setTaskError] = useState<string | null>(null);
  const fetching = useRef<Set<string>>(new Set());

  // restore an unfinished session saved in this browser (or start a new one)
  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    recordingStore.load(patientId).then((stored) => {
      if (cancelled) return;
      setSessions((s) => {
        if (s[patientId]) return s;
        // nothing recorded yet -> drop the saved task snapshot so the current task library is used
        const keepTasks = stored && Object.keys(stored.recordings).length > 0;
        const restored = stored ? { sessionId: stored.sessionId, recordings: stored.recordings, taskSet: keepTasks ? stored.taskSet : undefined } : newSession();
        return { ...s, [patientId]: restored };
      });
    });
    return () => { cancelled = true; };
  }, [patientId]);

  // mirror every change of the active session to IndexedDB
  const activeSession = patientId ? sessions[patientId] : undefined;
  useEffect(() => {
    if (patientId && activeSession) void recordingStore.save({ patientId, ...activeSession });
  }, [patientId, activeSession]);

  const update = useCallback((fn: (s: SessionState) => SessionState) => {
    if (!patientId) return;
    setSessions((all) => ({ ...all, [patientId]: fn(all[patientId] ?? newSession()) }));
  }, [patientId]);

  // a session without a task set (new, or saved before task snapshots existed) gets one from the API
  const needsTasks = !!activeSession && !activeSession.taskSet;
  useEffect(() => {
    if (!patientId || !needsTasks || fetching.current.has(patientId)) return;
    fetching.current.add(patientId);
    setTaskError(null);
    api.tasks(patientId)
      .then((ts) => update((s) => (s.taskSet ? s : { ...s, taskSet: ts })))
      .catch((e: Error) => setTaskError(e.message))
      .finally(() => fetching.current.delete(patientId));
  }, [patientId, needsTasks, update]);

  const saveRecording = useCallback((rec: Omit<Recording, "analysisId">) => {
    update((s) => ({ ...s, recordings: { ...s.recordings, [rec.key]: rec } }));
  }, [update]);

  const removeRecording = useCallback((key: string) => {
    update((s) => {
      const recordings = { ...s.recordings };
      delete recordings[key];
      return { ...s, recordings };
    });
  }, [update]);

  const markAnalysed = useCallback((key: string, analysisId: string) => {
    update((s) => (s.recordings[key] ? { ...s, recordings: { ...s.recordings, [key]: { ...s.recordings[key], analysisId } } } : s));
  }, [update]);

  const resetSession = useCallback(() => {
    if (patientId) void recordingStore.remove(patientId);
    update(() => newSession());
  }, [patientId, update]);

  const session = patientId ? sessions[patientId] ?? null : null;
  const taskSet = session?.taskSet ?? null;
  const required = useMemo(() => (taskSet ? requiredItems(taskSet) : []), [taskSet]);
  const completedCount = required.filter((r) => session?.recordings[r.key]).length;

  const value = useMemo<AssessmentState>(() => ({
    taskSet,
    taskError,
    session,
    required,
    completedCount,
    allRecorded: required.length > 0 && completedCount === required.length,
    saveRecording,
    removeRecording,
    markAnalysed,
    resetSession,
  }), [taskSet, taskError, session, required, completedCount, saveRecording, removeRecording, markAnalysed, resetSession]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAssessment(): AssessmentState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAssessment must be used inside <AssessmentProvider>");
  return ctx;
}
