import { useCallback, useEffect, useRef, useState } from "react";
import { FeedbackMessage, LiveMetric } from "../types/therapy";
import { buildTherapyWsUrl } from "./therapyApi";

const SEND_INTERVAL_MS = 500;
const SPEAKING_THRESHOLD = 0.015;

// Syllable-nucleus detection on the loudness envelope (runs in the browser;
// only the count is sent). A syllable is counted when the smoothed energy
// rises above a floor and then falls by at least 35% from that peak, with
// peaks at least 120 ms apart (speech rarely exceeds ~8 syllables/second).
const SYLLABLE_FRAME_MS = 20;
const SYLLABLE_FLOOR = SPEAKING_THRESHOLD * 1.5;
const SYLLABLE_DROP = 0.65;
const SYLLABLE_MIN_GAP_MS = 120;

function rmsOf(data: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    const v = (data[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / data.length);
}

export function useLiveFeedback(sessionId: string, exerciseType: "pacing" | "daf") {
  const [isActive, setIsActive] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<number | null>(null);
  const syllableTimerRef = useRef<number | null>(null);
  const syllableCountRef = useRef(0);

  const stop = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (syllableTimerRef.current !== null) {
      window.clearInterval(syllableTimerRef.current);
      syllableTimerRef.current = null;
    }
    socketRef.current?.close();
    socketRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close();
    }
    audioContextRef.current = null;
    setIsActive(false);
  }, []);

  const start = useCallback(async () => {
    setPermissionError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

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

      socket.onopen = () => {
        const dataArray = new Uint8Array(analyser.fftSize);
        const frame = new Uint8Array(analyser.fftSize);
        let envelope = 0;
        let localMax = 0;
        let lastPeak = 0;
        syllableCountRef.current = 0;
        syllableTimerRef.current = window.setInterval(() => {
          analyser.getByteTimeDomainData(frame);
          envelope = 0.6 * envelope + 0.4 * rmsOf(frame);
          const now = performance.now();
          if (envelope > localMax) localMax = envelope;
          if (localMax > SYLLABLE_FLOOR && envelope < localMax * SYLLABLE_DROP) {
            if (now - lastPeak > SYLLABLE_MIN_GAP_MS) {
              syllableCountRef.current += 1;
              lastPeak = now;
            }
            localMax = envelope;
          } else if (localMax <= SYLLABLE_FLOOR) {
            localMax = envelope;
          }
        }, SYLLABLE_FRAME_MS);

        intervalRef.current = window.setInterval(() => {
          analyser.getByteTimeDomainData(dataArray);

          let sumSquares = 0;
          let zeroCrossings = 0;
          for (let i = 0; i < dataArray.length; i++) {
            const normalized = (dataArray[i] - 128) / 128;
            sumSquares += normalized * normalized;
            if (i > 0) {
              const prev = (dataArray[i - 1] - 128) / 128;
              if ((prev >= 0 && normalized < 0) || (prev < 0 && normalized >= 0)) {
                zeroCrossings++;
              }
            }
          }
          const rms = Math.sqrt(sumSquares / dataArray.length);
          const zcr = zeroCrossings / dataArray.length;

          const metric: LiveMetric = {
            timestamp_ms: Date.now(),
            rms_energy: rms,
            zero_crossing_rate: zcr,
            is_speaking: rms > SPEAKING_THRESHOLD,
            syllables: syllableCountRef.current,
          };
          syllableCountRef.current = 0;

          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(metric));
          }
        }, SEND_INTERVAL_MS);
      };

      setIsActive(true);
    } catch (err) {
      setPermissionError(err instanceof Error ? err.message : "Microphone access failed.");
    }
  }, [sessionId, exerciseType]);

  useEffect(() => stop, [stop]);

  return { isActive, feedback, permissionError, start, stop };
}
