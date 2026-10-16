/**
 * Decides, 50 times a second, whether the microphone is hearing a voice.
 *
 * Loudness alone is not enough: a fan, a hum or typing can be as loud as soft
 * speech, and a silent attempt would then be scored as if the student had read.
 * A 20 ms frame counts as voiced only when both hold:
 *
 *   1. Louder than the room. The first CALIBRATION_MS ("get ready — stay
 *      quiet") measure the background; speech must be NOISE_MARGIN × louder
 *      than the 90th-percentile background frame (so noise that wobbles up
 *      and down doesn't count), and never quieter than MIN_THRESHOLD. If the
 *      student talked during "get ready" (loud and quiet frames differ a lot),
 *      the quiet gaps between their words estimate the room instead, and the
 *      bar is capped at MAX_ROOM_THRESHOLD. A slow floor tracker raises the
 *      bar if the room gets noisier later.
 *   2. Shaped like a voice. At least SPEECH_BAND_SHARE of the sound energy is
 *      in the speech band (150–4000 Hz), which rules out low hum and rumble.
 */

export const FRAME_MS = 20;
export const CALIBRATION_MS = 1500;
const CALIBRATION_FRAMES = CALIBRATION_MS / FRAME_MS;
const MIN_THRESHOLD = 0.008;
const MAX_ROOM_THRESHOLD = 0.04;
const NOISE_MARGIN = 2.5;
/** p90 / p10 above this during "get ready" means someone was speaking. */
const SPEECH_SPREAD = 4;
const GAP_MARGIN = 4;
const FLOOR_WINDOW = 250; // 5 s of frames for the slow floor tracker
const FLOOR_MARGIN = 3;
const SPEECH_BAND: [number, number] = [150, 4000];
const FULL_BAND: [number, number] = [50, 8000];
const SPEECH_BAND_SHARE = 0.55;

/** An attempt counts as "heard" only with at least this much voiced time… */
export const MIN_VOICED_SECONDS = 2;
/** …and at least this share of the attempt voiced. */
export const MIN_VOICED_SHARE = 0.1;

function percentile(values: number[], p: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * p))];
}

export interface VoiceFrame {
  rms: number;
  voiced: boolean;
  calibrating: boolean;
  zcr: number;
}

export class VoiceDetector {
  private readonly time: Uint8Array<ArrayBuffer>;
  private readonly freq: Float32Array<ArrayBuffer>;
  private readonly binHz: number;
  private readonly calibration: number[] = [];
  private readonly history: number[] = [];
  private roomThreshold = MIN_THRESHOLD;
  threshold = MIN_THRESHOLD;
  voicedFrames = 0;
  measuredFrames = 0;

  constructor(private readonly analyser: AnalyserNode) {
    this.time = new Uint8Array(analyser.fftSize);
    this.freq = new Float32Array(analyser.frequencyBinCount);
    this.binHz = analyser.context.sampleRate / analyser.fftSize;
  }

  get calibrating(): boolean {
    return this.calibration.length < CALIBRATION_FRAMES;
  }

  /** Seconds of voice heard so far (after calibration). */
  get voicedSeconds(): number {
    return (this.voicedFrames * FRAME_MS) / 1000;
  }

  /** True when the attempt contained enough real speech to be scored. */
  get heardSpeech(): boolean {
    return (
      this.voicedSeconds >= MIN_VOICED_SECONDS &&
      this.measuredFrames > 0 &&
      this.voicedFrames / this.measuredFrames >= MIN_VOICED_SHARE
    );
  }

  private bandEnergy([lo, hi]: [number, number]): number {
    let sum = 0;
    const from = Math.max(1, Math.floor(lo / this.binHz));
    const to = Math.min(this.freq.length - 1, Math.ceil(hi / this.binHz));
    for (let i = from; i <= to; i++) sum += 10 ** (this.freq[i] / 10);
    return sum;
  }

  /** Read one frame from the analyser and classify it. */
  frame(): VoiceFrame {
    this.analyser.getByteTimeDomainData(this.time);
    let sum = 0;
    let crossings = 0;
    for (let i = 0; i < this.time.length; i++) {
      const v = (this.time[i] - 128) / 128;
      sum += v * v;
      if (i > 0 && (this.time[i - 1] >= 128) !== (this.time[i] >= 128)) crossings++;
    }
    const rms = Math.sqrt(sum / this.time.length);
    const zcr = crossings / this.time.length;

    if (this.calibrating) {
      this.calibration.push(rms);
      if (!this.calibrating) {
        const p10 = percentile(this.calibration, 0.1);
        const p90 = percentile(this.calibration, 0.9);
        const room = p90 > SPEECH_SPREAD * Math.max(p10, 1e-4)
          ? p10 * GAP_MARGIN // talked during "get ready": use the gaps between words
          : p90 * NOISE_MARGIN; // a quiet room, even if the noise wobbles
        this.roomThreshold = Math.min(MAX_ROOM_THRESHOLD, Math.max(MIN_THRESHOLD, room));
        this.threshold = this.roomThreshold;
      }
      return { rms, voiced: false, calibrating: true, zcr };
    }

    this.history.push(rms);
    if (this.history.length > FLOOR_WINDOW) this.history.shift();
    const floor = this.history.length >= 50 ? percentile(this.history, 0.1) * FLOOR_MARGIN : 0;
    this.threshold = Math.max(this.roomThreshold, floor);

    let voiced = rms > this.threshold;
    if (voiced) {
      this.analyser.getFloatFrequencyData(this.freq);
      const total = this.bandEnergy(FULL_BAND);
      voiced = total > 0 && this.bandEnergy(SPEECH_BAND) / total >= SPEECH_BAND_SHARE;
    }
    this.measuredFrames += 1;
    if (voiced) this.voicedFrames += 1;
    return { rms, voiced, calibrating: false, zcr };
  }
}
