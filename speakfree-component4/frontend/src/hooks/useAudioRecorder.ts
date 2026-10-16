import { useCallback, useRef, useState } from "react";
import { FRAME_MS, VoiceDetector } from "./voiceDetector";

interface UseAudioRecorderReturn {
  isRecording: boolean;
  isPaused: boolean;
  audioBlob: Blob | null;
  audioUrl: string | null;
  recordingTime: number;
  analyserNode: AnalyserNode | null;
  permissionError: string | null;
  /** Measuring the room's background noise at the start of a recording. */
  calibrating: boolean;
  /** The recording contains real speech (≥ 2 s of voice, not just noise). */
  heardSpeech: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  pauseRecording: () => void;
  resumeRecording: () => void;
  clearRecording: () => void;
}

function pickMimeType(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const type of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return "";
}

/** Microphone settings for live exercises: the browser's voice processing is
 *  switched off so the recording stays clean for the whole attempt.
 *  - Echo cancellation adapts within about a second and then removes speech
 *    that is also being played back (DAF plays your own voice, delayed).
 *  - Automatic gain turns the level down after the first loud moment.
 *  - Noise suppression can cut soft speech to silence, which the voice
 *    detector would read as long pauses. */
export const MIC_CONSTRAINTS: MediaStreamConstraints = {
  audio: {
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false,
    channelCount: 1,
  },
};

const RECORDING_BITS_PER_SECOND = 128_000;

/**
 * Creates and starts an AudioContext. Call it at the very start of a click
 * handler, before awaiting the microphone: browsers only let audio start
 * shortly after a click, and the permission prompt can use up that time,
 * leaving a context created afterwards silently "suspended" (no sound out,
 * and analysers that only read silence).
 */
export function createAudioContext(): AudioContext {
  const context = new AudioContext();
  if (context.state === "suspended") void context.resume();
  return context;
}

/** After the microphone prompt: make sure the context is really running. */
export async function ensureRunning(context: AudioContext): Promise<void> {
  if (context.state !== "running") await context.resume();
  if (context.state !== "running") {
    throw new Error("The browser blocked audio. Click the button once more to start.");
  }
}

/**
 * Records an already-open microphone stream so the student can listen back.
 * Returns a function that stops recording; `onReady` receives a playable URL.
 * The recording stays in the browser — it is never uploaded.
 */
export function recordStream(stream: MediaStream, onReady: (url: string) => void): () => void {
  if (typeof MediaRecorder === "undefined") return () => {};
  const mimeType = pickMimeType();
  const recorder = new MediaRecorder(stream, {
    ...(mimeType ? { mimeType } : {}),
    audioBitsPerSecond: RECORDING_BITS_PER_SECOND,
  });
  const chunks: Blob[] = [];
  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) chunks.push(event.data);
  };
  recorder.onstop = () => {
    if (chunks.length) onReady(URL.createObjectURL(new Blob(chunks, { type: mimeType || "audio/webm" })));
  };
  recorder.start(250);
  return () => {
    if (recorder.state !== "inactive") recorder.stop();
  };
}

/**
 * useAudioRecorder
 *
 * No auto-stop/timeout. MediaRecorder + chunk buffer live in refs so a
 * re-render never interrupts an in-progress recording. Exposes a live
 * AnalyserNode so a visualizer can keep animating during silence.
 */
export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [calibrating, setCalibrating] = useState(false);
  const [heardSpeech, setHeardSpeech] = useState(false);
  const voiceTimerRef = useRef<number | null>(null);

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
    if (voiceTimerRef.current !== null) window.clearInterval(voiceTimerRef.current);
    voiceTimerRef.current = null;
    setCalibrating(false);
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
    setHeardSpeech(false);

    // Created before the microphone prompt, while the click still allows audio.
    const audioContext = createAudioContext();
    audioContextRef.current = audioContext;
    try {
      const stream = await navigator.mediaDevices.getUserMedia(MIC_CONSTRAINTS);
      streamRef.current = stream;
      await ensureRunning(audioContext);
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      setAnalyserNode(analyser);

      // Listen for real speech (not background noise) while recording.
      const detector = new VoiceDetector(analyser);
      setCalibrating(true);
      let tick = 0;
      voiceTimerRef.current = window.setInterval(() => {
        if (mediaRecorderRef.current?.state === "paused") return;
        const f = detector.frame();
        if (++tick % 5 === 0) {
          setCalibrating(f.calibrating);
          setHeardSpeech(detector.heardSpeech);
        }
      }, FRAME_MS);

      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, {
        ...(mimeType ? { mimeType } : {}),
        audioBitsPerSecond: RECORDING_BITS_PER_SECOND,
      });

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        teardownStream();
        clearTimer();
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250);

      startTimestampRef.current = Date.now();
      timerIntervalRef.current = window.setInterval(() => {
        setRecordingTime((Date.now() - startTimestampRef.current) / 1000);
      }, 200);

      setIsRecording(true);
      setIsPaused(false);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Microphone access was denied or is unavailable.";
      setPermissionError(message);
      teardownStream();
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
    calibrating,
    heardSpeech,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
  };
}
