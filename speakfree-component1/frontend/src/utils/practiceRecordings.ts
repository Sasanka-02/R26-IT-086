/**
 * Therapy practice recordings, kept ONLY in this browser (IndexedDB "speakfree-practice").
 *
 * Every Component 4 exercise is recorded on the device so the learner can listen back to their own
 * attempts. Nothing here is uploaded – the backend still receives only the practice numbers. Each call
 * fails soft: with IndexedDB unavailable (private window, blocked storage) practice keeps working and
 * the recording simply isn't kept. Separate from the screening store (utils/recordingStore.ts).
 */
export interface PracticeRecording {
  id: string;
  patientId: string;
  exerciseId: string;
  exerciseTitle: string;
  exerciseType: string;
  createdAt: string; // ISO
  durationSec: number;
  score: number | null;
  blob: Blob;
}

const DB_NAME = "speakfree-practice";
const STORE = "recordings";
let dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "id" }).createIndex("patientId", "patientId");
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

export const practiceRecordings = {
  /** Newest first; optionally only one exercise. */
  async list(patientId: string, exerciseId?: string): Promise<PracticeRecording[]> {
    try {
      const all = await run<PracticeRecording[]>("readonly", (s) => s.index("patientId").getAll(patientId));
      return all.filter((r) => !exerciseId || r.exerciseId === exerciseId).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    } catch {
      return [];
    }
  },
  async save(rec: PracticeRecording): Promise<boolean> {
    try {
      await run("readwrite", (s) => s.put(rec));
      return true;
    } catch {
      return false;
    }
  },
  async remove(id: string): Promise<void> {
    try {
      await run("readwrite", (s) => s.delete(id));
    } catch {
      /* ignore */
    }
  },
  async removeAll(patientId: string): Promise<void> {
    for (const r of await practiceRecordings.list(patientId)) await practiceRecordings.remove(r.id);
  },
};
