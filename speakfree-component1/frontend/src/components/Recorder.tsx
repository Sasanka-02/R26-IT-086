/**
 * Recorder – browser capture via MediaRecorder + a live Web Audio level meter.
 * The finished recording is handed to `onSave`; it is NOT uploaded here (that happens on "Analyse Now").
 *
 * Accuracy: the browser's own noise suppression and automatic gain control are OFF. They clip soft
 * word onsets and blur repeated sounds – exactly what Component 1 measures – and the backend already
 * does its own noise reduction and voice detection. Echo cancellation stays on.
 *
 * Mic check (noise robustness): before recording, 1 s of room noise is measured (noise floor, dBFS).
 * Right after Stop a quality check runs on the same live levels: too short, mostly silent, too quiet,
 * too loud (clipping) or too noisy (SNR ≈ loud speech frames − noise floor < 10 dB). Issues are shown
 * as friendly warnings – they never block the recording. Everything stays in the browser.
 *
 * Comfort: a calm "take your time" progress bar instead of a countdown, Space starts / stops, and
 * `big` gives larger controls for young children.
 */
import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Mic, RotateCcw, Square, Upload } from "lucide-react";

function pickMimeType(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  for (const c of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(c)) return c;
  }
  return "";
}
function extensionFor(mime: string): string {
  if (mime.includes("webm")) return ".webm";
  if (mime.includes("ogg")) return ".ogg";
  if (mime.includes("mp4")) return ".m4a";
  if (mime.includes("wav")) return ".wav";
  return ".webm";
}
export const fmtTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const BARS = 34;
const CHECK_MS = 1000;          // room-noise measurement before recording starts
const NOISY_ROOM_DBFS = -45;    // background noise above this level is a "noisy room"
const MIN_SNR_DB = 10;          // below this, the screening is less reliable
const MIN_SECONDS = 2;          // shorter recordings rarely contain enough speech
const QUIET_DBFS = -40;         // loud speech frames below this: voice too quiet / mic too far
const SPEECH_MARGIN_DB = 10;    // a frame counts as speech when it is this far above the noise floor
const MIN_SPEECH_SHARE = 0.15;  // less speech than this share of the recording: "mostly silent"
const CLIP_LEVEL = 0.99;        // sample peak at full scale
const MAX_CLIP_SHARE = 0.01;    // more clipped frames than this: "too loud"
const ENDING_SOON_SEC = 10;

const toDb = (rms: number) => 20 * Math.log10(Math.max(rms, 1e-6));
function percentile(values: number[], p: number): number {
  if (!values.length) return -120;
  const s = [...values].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor((p / 100) * s.length))];
}

interface Quality { snrDb: number | null; issues: string[] }

/** Friendly quality check of one recording from its live levels (dBFS per frame). */
function checkQuality(frameDb: number[], clippedFrames: number, noiseFloor: number, durationSec: number): Quality {
  const issues: string[] = [];
  if (durationSec < MIN_SECONDS) issues.push("That was very short – try saying a little more.");
  if (frameDb.length < 10) return { snrDb: null, issues };
  const loud = percentile(frameDb, 95);
  const snrDb = Math.round(loud - noiseFloor);
  const speechShare = frameDb.filter((d) => d > noiseFloor + SPEECH_MARGIN_DB).length / frameDb.length;
  if (clippedFrames / frameDb.length > MAX_CLIP_SHARE) issues.push("Your voice was too loud for the microphone – move back a little.");
  else if (loud < QUIET_DBFS) issues.push("Your voice was very quiet – move closer to the microphone or speak a bit louder.");
  if (speechShare < MIN_SPEECH_SHARE && durationSec >= MIN_SECONDS) issues.push("We could hardly hear any speech in this recording.");
  if (snrDb < MIN_SNR_DB) issues.push(`Too noisy (your voice was only about ${Math.max(0, snrDb)} dB above the background) – move somewhere quieter.`);
  return { snrDb, issues };
}

export interface SavedAudio {
  blob: Blob;
  filename: string;
  durationSec: number;
}

export default function Recorder({ maxSeconds, saved, onSave, onClear, onStart, disabled = false, big = false }: {
  maxSeconds: number;
  saved?: SavedAudio;
  onSave: (audio: SavedAudio) => void;
  onClear: () => void;
  onStart?: () => void; // e.g. pause a task video, so its sound is not recorded (or measured as room noise)
  disabled?: boolean;
  big?: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const [checking, setChecking] = useState(false);
  const [roomWarning, setRoomWarning] = useState(false);
  const [quality, setQuality] = useState<Quality | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef(0);
  const timerRef = useRef(0);
  const fileRef = useRef<HTMLInputElement>(null);
  const phaseRef = useRef<"check" | "record" | "idle">("idle");
  const roomDb = useRef<number[]>([]);
  const speechDb = useRef<number[]>([]);
  const clipped = useRef(0);

  // object URL for the saved recording's preview player
  useEffect(() => {
    if (!saved) return setUrl(null);
    const u = URL.createObjectURL(saved.blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [saved]);
  // a cleared recording loses its quality notes
  useEffect(() => { if (!saved) { setQuality(null); setRoomWarning(false); } }, [saved]);

  const cleanupStream = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    window.clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    ctxRef.current?.close().catch(() => undefined);
    ctxRef.current = null;
    setLevel(0);
  }, []);
  useEffect(() => () => {
    // unmounting mid-recording: discard rather than save
    if (recorderRef.current) recorderRef.current.onstop = null;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    cleanupStream();
  }, [cleanupStream]);

  const stop = useCallback(() => {
    window.clearInterval(timerRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") recorderRef.current.stop();
  }, []);

  const start = useCallback(async () => {
    onStart?.();
    setError(null);
    setRoomWarning(false);
    setQuality(null);
    roomDb.current = [];
    speechDb.current = [];
    clipped.current = 0;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        // raw signal for the analysis: no browser noise suppression / auto gain (see header comment)
        audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
      });
      streamRef.current = stream;

      const ctx = new AudioContext();
      ctxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Float32Array(analyser.fftSize);
      const tick = () => {
        analyser.getFloatTimeDomainData(data);
        let sum = 0;
        let peak = 0;
        for (let i = 0; i < data.length; i++) {
          sum += data[i] * data[i];
          peak = Math.max(peak, Math.abs(data[i]));
        }
        const rms = Math.sqrt(sum / data.length);
        if (phaseRef.current === "check") roomDb.current.push(toDb(rms));
        else if (phaseRef.current === "record") {
          speechDb.current.push(toDb(rms));
          if (peak >= CLIP_LEVEL) clipped.current += 1;
        }
        setLevel(Math.min(1, rms * 8));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();

      // 1) mic check: measure the room for a moment before recording
      phaseRef.current = "check";
      setChecking(true);
      await new Promise((r) => window.setTimeout(r, CHECK_MS));
      setChecking(false);
      if (!streamRef.current) return; // unmounted / cancelled during the check
      const noiseFloor = percentile(roomDb.current, 50);
      setRoomWarning(noiseFloor > NOISY_ROOM_DBFS);
      phaseRef.current = "record";

      // 2) record
      const mime = pickMimeType();
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks: BlobPart[] = [];
      const startedAt = Date.now();
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = () => {
        phaseRef.current = "idle";
        const durationSec = (Date.now() - startedAt) / 1000;
        setQuality(checkQuality(speechDb.current, clipped.current, noiseFloor, durationSec));
        const type = rec.mimeType || mime || "audio/webm";
        onSave({ blob: new Blob(chunks, { type }), filename: `recording${extensionFor(type)}`, durationSec });
        setRecording(false);
        cleanupStream();
      };
      recorderRef.current = rec;
      rec.start(250);
      setElapsed(0);
      setRecording(true);
      timerRef.current = window.setInterval(() => {
        const s = (Date.now() - startedAt) / 1000;
        setElapsed(s);
        if (s >= maxSeconds) stop();
      }, 200);
    } catch {
      phaseRef.current = "idle";
      setChecking(false);
      setError("Microphone access was blocked. Allow microphone permission in your browser and try again.");
      cleanupStream();
    }
  }, [cleanupStream, maxSeconds, onSave, onStart, stop]);

  // Space starts / stops recording (not while typing in a field or focused on another control)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat || disabled || checking) return;
      const el = e.target as HTMLElement | null;
      if (el && (["INPUT", "TEXTAREA", "SELECT", "BUTTON", "AUDIO", "A"].includes(el.tagName) || el.isContentEditable)) return;
      if (recording) { e.preventDefault(); stop(); }
      else if (!saved) { e.preventDefault(); void start(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [checking, disabled, recording, saved, start, stop]);

  function onFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setQuality(null);
    setRoomWarning(false);
    const probe = new Audio();
    const u = URL.createObjectURL(f);
    probe.preload = "metadata";
    const done = (d: number) => { URL.revokeObjectURL(u); onSave({ blob: f, filename: f.name, durationSec: Number.isFinite(d) ? d : 0 }); };
    probe.onloadedmetadata = () => done(probe.duration);
    probe.onerror = () => done(0);
    probe.src = u;
  }

  const remaining = Math.max(0, maxSeconds - elapsed);
  const btn = big ? "rounded-2xl py-4 text-lg" : "py-3";

  return (
    <div className="flex flex-col items-center gap-4">
      {/* mic circle */}
      <div className={`grid place-items-center rounded-full ${big ? "h-28 w-28" : "h-24 w-24"} ${saved && !recording ? "bg-ok-soft" : "bg-lav-100"} ${recording ? "recording-pulse" : ""}`}>
        {saved && !recording ? <CheckCircle2 size={40} className="text-ok" /> : <Mic size={big ? 48 : 40} className="text-lav-500" />}
      </div>

      {/* waveform bars */}
      <div className="flex h-12 w-full items-center justify-center gap-[3px]" aria-hidden>
        {Array.from({ length: BARS }).map((_, i) => {
          const idle = 0.12 + 0.55 * Math.abs(Math.sin(i * 0.55)) * Math.abs(Math.cos(i * 0.23));
          const h = recording ? Math.max(0.08, level * (0.35 + 0.65 * Math.abs(Math.sin(i * 0.8 + elapsed * 7)))) : idle;
          return <span key={i} className={`w-[3px] rounded-full ${recording ? "bg-lav-500" : saved ? "bg-ok/40" : "bg-lav-400/60"}`} style={{ height: `${Math.max(4, h * 46)}px` }} />;
        })}
      </div>

      {/* calm timer: elapsed + a soft bar, no countdown pressure */}
      {recording ? (
        <div className="w-full">
          <div className="h-1.5 w-full rounded-full bg-lav-100">
            <div className="h-1.5 rounded-full bg-lav-400 transition-[width] duration-200" style={{ width: `${Math.min(100, (elapsed / maxSeconds) * 100)}%` }} />
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-ink-soft">
            <span className="font-mono">{fmtTime(elapsed)}</span>
            <span>{remaining <= ENDING_SOON_SEC ? `About ${Math.ceil(remaining)} seconds left – finish your sentence` : "Take your time"}</span>
          </div>
        </div>
      ) : (
        <div className="text-sm text-ink-soft">
          {saved ? <span className="font-mono">{fmtTime(saved.durationSec)}</span> : <>Speak for up to {fmtTime(maxSeconds)} · no rush</>}
        </div>
      )}

      {error && <p className="w-full rounded-lg bg-bad-soft px-3 py-2 text-xs text-bad">{error}</p>}
      {checking && (
        <p className="flex w-full items-center gap-2 rounded-lg bg-lav-50 px-3 py-2 text-xs text-ink" role="status">
          <Loader2 size={14} className="animate-spin text-lav-500" /> Checking the room… please stay quiet for a moment.
        </p>
      )}
      {roomWarning && recording && (
        <p className="flex w-full items-start gap-2 rounded-lg bg-warn-soft px-3 py-2 text-xs text-warn" role="status">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" /> It's quite noisy here. If you can, move somewhere quieter or closer to the microphone.
        </p>
      )}
      {saved && !recording && quality && (
        quality.issues.length ? (
          <div className="w-full rounded-lg bg-warn-soft px-3 py-2 text-xs text-warn" role="status">
            <div className="flex items-center gap-2 font-semibold"><AlertTriangle size={14} className="shrink-0" /> For the most accurate result, please record again:</div>
            <ul className="mt-1 list-disc space-y-0.5 pl-6">{quality.issues.map((i) => <li key={i}>{i}</li>)}</ul>
          </div>
        ) : (
          <p className="flex w-full items-center gap-2 rounded-lg bg-ok-soft px-3 py-2 text-xs text-ok" role="status">
            <CheckCircle2 size={14} /> Good recording{quality.snrDb !== null ? ` – your voice came through clearly (about ${quality.snrDb} dB above the background)` : ""}.
          </p>
        )
      )}

      {checking ? (
        <button className={`btn-primary w-full ${btn}`} disabled><Loader2 size={15} className="animate-spin" /> Checking microphone…</button>
      ) : recording ? (
        <button className={`btn-primary w-full bg-bad hover:bg-red-700 ${btn}`} onClick={stop}><Square size={15} /> Stop Recording</button>
      ) : saved ? (
        <div className="w-full space-y-2">
          {url && <audio controls src={url} className="h-10 w-full" />}
          <button className={`w-full ${quality?.issues.length ? "btn-primary" : "btn-ghost"}`} onClick={onClear} disabled={disabled}><RotateCcw size={15} /> Record again</button>
        </div>
      ) : (
        <div className="flex w-full gap-2">
          <button className={`btn-primary flex-1 ${btn}`} onClick={() => void start()} disabled={disabled}>
            <span className="h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white/70" /> Start Recording
          </button>
          <button className="btn-ghost px-3" onClick={() => fileRef.current?.click()} disabled={disabled} title="Upload an audio file (.wav, .webm, .m4a)">
            <Upload size={16} />
          </button>
          <input ref={fileRef} type="file" accept=".wav,.webm,.ogg,.m4a,.mp3,audio/*" className="hidden" onChange={onFile} />
        </div>
      )}
      {!recording && !saved && !checking && <p className="text-[11px] muted">Tip: press <kbd className="rounded border border-line bg-canvas px-1 font-mono">Space</kbd> to start and stop.</p>}
    </div>
  );
}
