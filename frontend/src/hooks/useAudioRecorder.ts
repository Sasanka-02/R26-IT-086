import { useCallback, useRef, useState } from "react";

interface UseAudioRecorderReturn {
  isRecording: boolean;
  isPaused: boolean;
  audioBlob: Blob | null;
  audioUrl: string | null;
  recordingTime: number;
  analyserNode: AnalyserNode | null;
  permissionError: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  pauseRecording: () => void;
  resumeRecording: () => void;
  clearRecording: () => void;
}

/**
 * Picks the best-supported MIME type for MediaRecorder.
 * Prefers opus/webm; falls back for iOS Safari which does not support webm.
 */
function pickMimeType(): string {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  for (const type of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return "";
}

/**
 * useAudioRecorder
 *
 * Clinical UX constraints this hook enforces:
 *  - No auto-stop / no timeout. Caller always decides when to stop.
 *  - MediaRecorder instance + chunk buffer live in refs, not state, so a
 *    re-render (e.g. from the visualizer updating) never interrupts or
 *    corrupts an in-progress recording.
 *  - Exposes a live AnalyserNode so a visualizer can keep animating even
 *    during silent stuttering blocks (silence != "frozen app").
 */
export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const startTimestampRef = useRef<number>(0);

  const clearTimer = useCallback(() => {
    if (timerIntervalRef.current !== null) {
      window.clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  }, []);

  const teardownStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close();
    }
    audioContextRef.current = null;
  }, []);

  const startRecording = useCallback(async () => {
    setPermissionError(null);
    chunksRef.current = [];
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Web Audio graph for the live visualizer
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      setAnalyserNode(analyser);

      const mimeType = pickMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mimeType || "audio/webm",
        });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        teardownStream();
        clearTimer();
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250); // collect chunks every 250ms

      startTimestampRef.current = Date.now();
      timerIntervalRef.current = window.setInterval(() => {
        setRecordingTime((Date.now() - startTimestampRef.current) / 1000);
      }, 200);

      setIsRecording(true);
      setIsPaused(false);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Microphone access was denied or is unavailable.";
      setPermissionError(message);
      setIsRecording(false);
    }
  }, [clearTimer, teardownStream]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setIsPaused(false);
  }, []);

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause();
      clearTimer();
      setIsPaused(true);
    }
  }, [clearTimer]);

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume();
      startTimestampRef.current = Date.now() - recordingTime * 1000;
      timerIntervalRef.current = window.setInterval(() => {
        setRecordingTime((Date.now() - startTimestampRef.current) / 1000);
      }, 200);
      setIsPaused(false);
    }
  }, [recordingTime]);

  const clearRecording = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    setAnalyserNode(null);
    chunksRef.current = [];
    mediaRecorderRef.current = null;
    teardownStream();
    clearTimer();
    setIsRecording(false);
    setIsPaused(false);
  }, [audioUrl, teardownStream, clearTimer]);

  return {
    isRecording,
    isPaused,
    audioBlob,
    audioUrl,
    recordingTime,
    analyserNode,
    permissionError,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
  };
}
