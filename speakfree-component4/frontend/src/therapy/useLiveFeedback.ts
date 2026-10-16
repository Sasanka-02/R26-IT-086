import { useCallback, useEffect, useRef, useState } from "react";
import { FeedbackMessage, LiveMetric } from "../types/therapy";
import { buildTherapyWsUrl } from "./therapyApi";
import { createAudioContext, ensureRunning, MIC_CONSTRAINTS, recordStream } from "../hooks/useAudioRecorder";
import { FRAME_MS, VoiceDetector } from "../hooks/voiceDetector";

const SEND_INTERVAL_MS = 500;
// A 500 ms interval counts as "speaking" when at least a quarter of its 20 ms
// frames are voiced, so the short gaps between words don't register as silence.
const VOICED_SHARE = 0.25;

// Syllable-nucleus detection on the loudness envelope of voiced frames (runs
// in the browser; only the count is sent). A syllable is counted when the
// smoothed energy rises above 1.5 × the voice threshold and then falls by at
// least 35% from that peak, with peaks at least 120 ms apart (speech rarely
// exceeds ~8 syllables/second).
const SYLLABLE_DROP = 0.65;
const SYLLABLE_MIN_GAP_MS = 120;

export function useLiveFeedback(sessionId: string, exerciseType: "pacing" | "daf") {
  const [isActive, setIsActive] = useState(false);
  /** True for the first moments while the room's background noise is measured. */
  const [calibrating, setCalibrating] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<number | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const stopRecordingRef = useRef<(() => void) | null>(null);
  const detectorRef = useRef<VoiceDetector | null>(null);

  const stop = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (frameTimerRef.current !== null) {
      window.clearInterval(frameTimerRef.current);
      frameTimerRef.current = null;
    }
    socketRef.current?.close();
    socketRef.current = null;
    // Stop the recorder before the tracks, so the last chunk is kept.
    stopRecordingRef.current?.();
    stopRecordingRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close();
    }
    audioContextRef.current = null;
    setCalibrating(false);
    setIsActive(false);
  }, []);

  const start = useCallback(async () => {
    setPermissionError(null);
    setRecordingUrl(null);
    detectorRef.current = null;
    // Created before the microphone prompt, while the click still allows audio:
    // a context left "suspended" gives an analyser that only reads silence.
    const audioContext = createAudioContext();
    audioContextRef.current = audioContext;
    try {
      const stream = await navigator.mediaDevices.getUserMedia(MIC_CONSTRAINTS);
      streamRef.current = stream;
      await ensureRunning(audioContext);
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      const detector = new VoiceDetector(analyser);
      detectorRef.current = detector;

      stopRecordingRef.current = recordStream(stream, setRecordingUrl);

      const socket = new WebSocket(buildTherapyWsUrl(sessionId, exerciseType));
      socketRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const parsed: FeedbackMessage = JSON.parse(event.data);
          setFeedback(parsed);
        } catch {
          // ignore malformed frames
        }
      };

      setCalibrating(true);
      let envelope = 0;
      let localMax = 0;
      let lastPeak = 0;
      let syllables = 0;
      let window_ = { frames: 0, voiced: 0, voicedEnergy: 0, energy: 0, zcr: 0 };

      frameTimerRef.current = window.setInterval(() => {
        const f = detector.frame();
        if (f.calibrating) return;
        setCalibrating(false);

        window_.frames += 1;
        window_.energy += f.rms;
        window_.zcr += f.zcr;
        if (f.voiced) {
          window_.voiced += 1;
          window_.voicedEnergy += f.rms;
        }

        // Only voiced frames feed the syllable counter, so noise can't add syllables.
        envelope = 0.6 * envelope + 0.4 * (f.voiced ? f.rms : 0);
        const floor = detector.threshold * 1.5;
        const now = performance.now();
        if (envelope > localMax) localMax = envelope;
        if (localMax > floor && envelope < localMax * SYLLABLE_DROP) {
          if (now - lastPeak > SYLLABLE_MIN_GAP_MS) {
            syllables += 1;
            lastPeak = now;
          }
          localMax = envelope;
        } else if (localMax <= floor) {
          localMax = envelope;
        }
      }, FRAME_MS);

      intervalRef.current = window.setInterval(() => {
        const w = window_;
        window_ = { frames: 0, voiced: 0, voicedEnergy: 0, energy: 0, zcr: 0 };
        if (w.frames === 0) return; // still measuring the room
        const speaking = w.voiced / w.frames >= VOICED_SHARE;
        const metric: LiveMetric = {
          timestamp_ms: Date.now(),
          // Loudness of the voice itself (not diluted by the gaps between words).
          rms_energy: speaking ? w.voicedEnergy / w.voiced : w.energy / w.frames,
          zero_crossing_rate: w.zcr / w.frames,
          is_speaking: speaking,
          syllables,
        };
        syllables = 0;
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify(metric));
        }
      }, SEND_INTERVAL_MS);

      setIsActive(true);
    } catch (err) {
      stop();
      setPermissionError(err instanceof Error ? err.message : "Microphone access failed.");
    }
  }, [sessionId, exerciseType, stop]);

  useEffect(() => stop, [stop]);

  /** True when the attempt had too little real speech to be scored. */
  const heardNothing = () => !(detectorRef.current?.heardSpeech ?? false);

  return { isActive, calibrating, feedback, permissionError, recordingUrl, heardNothing, start, stop };
}
