/**
 * Browser-only persistence for in-progress screening sessions (IndexedDB).
 *
 * Recordings survive a page reload until "Analyse Now" completes; the session is then deleted
 * (see AssessmentContext.resetSession). Nothing here is ever sent anywhere except by the analysis
 * upload itself. Every call fails soft: if IndexedDB is unavailable (private window, blocked
 * storage) the app keeps working with in-memory recordings only.
 */
import type { TaskSet, TaskType } from "../types";

export interface StoredRecording {
  key: string;
  taskType: TaskType;
  taskId: string;
  blob: Blob;
  filename: string;
  durationSec: number;
  analysisId?: string;
}

export interface StoredSession {
  patientId: string;
  sessionId: string;
  recordings: Record<string, StoredRecording>;
  taskSet?: TaskSet; // the tasks this session was started with (tasks rotate between sessions)
}

const DB_NAME = "speakfree";
const STORE = "sessions";

let dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "patientId" });
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    dbPromise.catch(() => { dbPromise = null; });
  }
  return dbPromise;
}

async function run<T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const req = fn(db.transaction(STORE, mode).objectStore(STORE));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export const recordingStore = {
  async load(patientId: string): Promise<StoredSession | null> {
    try {
      return (await run<StoredSession | undefined>("readonly", (s) => s.get(patientId))) ?? null;
    } catch {
      return null;
    }
  },
  async save(session: StoredSession): Promise<void> {
    try {
      await run("readwrite", (s) => s.put(session));
    } catch {
      /* storage unavailable – recordings stay in memory for this tab */
    }
  },
  async remove(patientId: string): Promise<void> {
    try {
      await run("readwrite", (s) => s.delete(patientId));
    } catch {
      /* ignore */
    }
  },
};
