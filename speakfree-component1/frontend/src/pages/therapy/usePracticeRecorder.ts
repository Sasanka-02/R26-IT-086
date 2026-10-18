/**
 * usePracticeRecorder – records the learner's voice during any therapy exercise (MediaRecorder).
 * The audio stays in the browser: stop() resolves with the Blob, which ExerciseSession keeps in
 * IndexedDB (utils/practiceRecordings.ts). It uses its own microphone stream, so it works next to
 * the live coach, the DAF delay node and the word rounds.
 */
import { useCallback, useEffect, useRef } from "react";

export function usePracticeRecorder() {
  const ref = useRef<{ rec: MediaRecorder; stream: MediaStream; chunks: Blob[] } | null>(null);

  const discard = useCallback(() => {
    const cur = ref.current;
    ref.current = null;
    if (!cur) return;
    cur.rec.ondataavailable = null;
    cur.rec.onstop = null;
    if (cur.rec.state !== "inactive") cur.rec.stop();
    cur.stream.getTracks().forEach((t) => t.stop());
  }, []);

  /** Start recording; resolves false when the microphone or MediaRecorder isn't available. */
  const start = useCallback(async (): Promise<boolean> => {
    discard();
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) return false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.start(1000);
      ref.current = { rec, stream, chunks };
      return true;
    } catch {
      return false;
    }
  }, [discard]);

  /** Stop and return the recording (null if nothing was recorded). */
  const stop = useCallback((): Promise<Blob | null> => {
    const cur = ref.current;
    ref.current = null;
    if (!cur) return Promise.resolve(null);
    return new Promise((resolve) => {
      const done = () => {
        cur.stream.getTracks().forEach((t) => t.stop());
        resolve(cur.chunks.length ? new Blob(cur.chunks, { type: cur.rec.mimeType || "audio/webm" }) : null);
      };
      if (cur.rec.state === "inactive") return done();
      cur.rec.onstop = done;
      cur.rec.stop();
    });
  }, []);

  useEffect(() => discard, [discard]);
  return { start, stop, discard };
}
