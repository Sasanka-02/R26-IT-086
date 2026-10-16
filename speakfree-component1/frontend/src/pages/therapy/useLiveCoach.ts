/**
 * useLiveCoach – live practice metrics computed IN THE BROWSER (Component 4, SO1).
 * Every 500 ms the RMS energy, zero-crossing rate, a voicing flag and a syllable-peak count are
 * sent to /ws/therapy-live; the server answers with short coaching messages. Audio never leaves
 * the device. Also exposes the live loudness (for the meter) and the longest voiced run.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/client";

const SEND_MS = 500;
const SPEAKING = 0.015;
const SYL_FRAME_MS = 20;
const SYL_FLOOR = SPEAKING * 1.5;
const SYL_DROP = 0.65;
const SYL_GAP_MS = 120;

export interface CoachMessage { type: string; message: string; severity: string }
export interface LiveStats { voicedFrames: number; frames: number; syllables: number; longestRunSec: number }

function rms(data: Uint8Array): number {
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    const v = (data[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / data.length);
}

export function useLiveCoach(exerciseType: string) {
  const [active, setActive] = useState(false);
  const [message, setMessage] = useState<CoachMessage | null>(null);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const liveId = useRef(`live-${crypto.randomUUID()}`);
  const stats = useRef<LiveStats>({ voicedFrames: 0, frames: 0, syllables: 0, longestRunSec: 0 });
  const cleanup = useRef<() => void>(() => {});

  const stop = useCallback(() => {
    cleanup.current();
    cleanup.current = () => {};
    setActive(false);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setMessage(null);
    liveId.current = `live-${crypto.randomUUID()}`;
    stats.current = { voicedFrames: 0, frames: 0, syllables: 0, longestRunSec: 0 };
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Microphone access failed.");
      return;
    }
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const socket = new WebSocket(api.therapy.liveUrl(liveId.current, exerciseType));
    socket.onmessage = (ev) => {
      try { setMessage(JSON.parse(ev.data)); } catch { /* ignore malformed frames */ }
    };

    const frame = new Uint8Array(analyser.fftSize);
    let envelope = 0, localMax = 0, lastPeak = 0, sylCount = 0, run = 0;
    const sylTimer = window.setInterval(() => {
      analyser.getByteTimeDomainData(frame);
      envelope = 0.6 * envelope + 0.4 * rms(frame);
      const now = performance.now();
      if (envelope > localMax) localMax = envelope;
      if (localMax > SYL_FLOOR && envelope < localMax * SYL_DROP) {
        if (now - lastPeak > SYL_GAP_MS) { sylCount += 1; lastPeak = now; }
        localMax = envelope;
      } else if (localMax <= SYL_FLOOR) {
        localMax = envelope;
      }
    }, SYL_FRAME_MS);

    const data = new Uint8Array(analyser.fftSize);
    const sendTimer = window.setInterval(() => {
      analyser.getByteTimeDomainData(data);
      let crossings = 0;
      for (let i = 1; i < data.length; i++) if ((data[i - 1] >= 128) !== (data[i] >= 128)) crossings++;
      const energy = rms(data);
      const speaking = energy > SPEAKING;
      setLevel(energy);
      const s = stats.current;
      s.frames += 1;
      s.syllables += sylCount;
      if (speaking) {
        s.voicedFrames += 1;
        run += 1;
        s.longestRunSec = Math.max(s.longestRunSec, (run * SEND_MS) / 1000);
      } else run = 0;
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ timestamp_ms: Date.now(), rms_energy: energy, zero_crossing_rate: crossings / data.length,
          is_speaking: speaking, syllables: sylCount }));
      }
      sylCount = 0;
    }, SEND_MS);

    cleanup.current = () => {
      window.clearInterval(sylTimer);
      window.clearInterval(sendTimer);
      socket.close();
      stream.getTracks().forEach((t) => t.stop());
      void ctx.close();
    };
    setActive(true);
  }, [exerciseType]);

  useEffect(() => stop, [stop]);

  return { active, message, level, error, start, stop, liveId, stats };
}
