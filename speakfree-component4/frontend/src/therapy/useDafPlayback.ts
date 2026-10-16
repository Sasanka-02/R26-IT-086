import { useCallback, useEffect, useRef, useState } from "react";
import { createAudioContext, ensureRunning, MIC_CONSTRAINTS, recordStream } from "../hooks/useAudioRecorder";
import { FRAME_MS, VoiceDetector } from "../hooks/voiceDetector";

/** Playback is boosted because the microphone runs without automatic gain
 *  (that keeps recordings clean); a limiter stops loud speech from distorting. */
const DEFAULT_VOLUME = 3;
/** Final output scale after the limiter (protects ears in headphones). */
const OUTPUT_CEILING = 0.5;

/**
 * Delayed auditory feedback: plays the microphone back through the speakers
 * or headphones after `delayMs`. Shared by DAF calibration and practice.
 *
 *   mic → delay → volume → limiter → output
 *   mic → level meter (and an optional recording for listening back)
 */
export function useDafPlayback({ record = false }: { record?: boolean } = {}) {
  const [active, setActive] = useState(false);
  const [level, setLevel] = useState(0);
  /** Real speech heard this session (≥ 2 s of voice, not background noise). */
  const [heardVoice, setHeardVoice] = useState(false);
  /** Measuring the room's background noise for the first moment. */
  const [calibrating, setCalibrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null);
  const [volume, setVolumeState] = useState(DEFAULT_VOLUME);

  const contextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const delayRef = useRef<DelayNode | null>(null);
  const gainRef = useRef<GainNode | null>(null);
  const meterRef = useRef<number | null>(null);
  const stopRecordingRef = useRef<(() => void) | null>(null);

  const stop = useCallback(() => {
    if (meterRef.current !== null) window.clearInterval(meterRef.current);
    meterRef.current = null;
    stopRecordingRef.current?.(); // before the tracks, so the last chunk is kept
    stopRecordingRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (contextRef.current && contextRef.current.state !== "closed") contextRef.current.close();
    contextRef.current = null;
    delayRef.current = null;
    gainRef.current = null;
    setLevel(0);
    setCalibrating(false);
    setActive(false);
  }, []);

  /** Call directly from a click handler. */
  const start = useCallback(
    async (delayMs: number) => {
      stop();
      setError(null);
      setHeardVoice(false);
      setRecordingUrl(null);
      // Created before the microphone prompt, while the click still allows audio.
      const context = createAudioContext();
      contextRef.current = context;
      try {
        const stream = await navigator.mediaDevices.getUserMedia(MIC_CONSTRAINTS);
        streamRef.current = stream;
        await ensureRunning(context);

        const source = context.createMediaStreamSource(stream);
        const delay = context.createDelay(2.0);
        delay.delayTime.value = delayMs / 1000;
        const gain = context.createGain();
        gain.gain.value = volume;
        const limiter = context.createDynamicsCompressor();
        limiter.threshold.value = -12;
        limiter.ratio.value = 20;
        // The compressor adds its own make-up gain; this keeps loud speech at a
        // comfortable level in headphones.
        const headroom = context.createGain();
        headroom.gain.value = OUTPUT_CEILING;
        source.connect(delay).connect(gain).connect(limiter).connect(headroom).connect(context.destination);

        const analyser = context.createAnalyser();
        analyser.fftSize = 1024;
        source.connect(analyser);
        const detector = new VoiceDetector(analyser);
        setCalibrating(true);
        let tick = 0;
        meterRef.current = window.setInterval(() => {
          const f = detector.frame();
          if (++tick % 5 === 0) {
            // Meter shows the voice only, so background noise doesn't look like speech.
            setLevel(f.voiced ? Math.min(1, f.rms * 12) : 0);
            setCalibrating(f.calibrating);
            setHeardVoice(detector.heardSpeech);
          }
        }, FRAME_MS);

        if (record) stopRecordingRef.current = recordStream(stream, setRecordingUrl);
        delayRef.current = delay;
        gainRef.current = gain;
        setActive(true);
      } catch (err) {
        stop();
        setError(err instanceof Error ? err.message : "Microphone access failed.");
      }
    },
    [record, stop, volume]
  );

  const setDelay = useCallback((delayMs: number) => {
    if (delayRef.current) delayRef.current.delayTime.value = delayMs / 1000;
  }, []);

  const setVolume = useCallback((value: number) => {
    setVolumeState(value);
    if (gainRef.current) gainRef.current.gain.value = value;
  }, []);

  useEffect(() => stop, [stop]);

  return { active, level, heardVoice, calibrating, error, recordingUrl, volume, start, stop, setDelay, setVolume };
}
