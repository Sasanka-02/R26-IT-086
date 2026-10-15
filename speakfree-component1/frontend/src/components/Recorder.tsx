/**
 * Recorder – browser capture via MediaRecorder + a live Web Audio level meter.
 * The finished recording is handed to `onSave`; it is NOT uploaded here (that happens on "Analyse Now").
 */
import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import { CheckCircle2, Mic, RotateCcw, Square, Upload } from "lucide-react";

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

export interface SavedAudio {
  blob: Blob;
  filename: string;
  durationSec: number;
}

export default function Recorder({ maxSeconds, saved, onSave, onClear, disabled = false }: {
  maxSeconds: number;
  saved?: SavedAudio;
  onSave: (audio: SavedAudio) => void;
  onClear: () => void;
  disabled?: boolean;
}) {
  const [recording, setRecording] = useState(false);
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

  // object URL for the saved recording's preview player
  useEffect(() => {
    if (!saved) return setUrl(null);
    const u = URL.createObjectURL(saved.blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [saved]);

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

  function stop() {
    window.clearInterval(timerRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") recorderRef.current.stop();
  }

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
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
        for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
        setLevel(Math.min(1, Math.sqrt(sum / data.length) * 6));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();

      const mime = pickMimeType();
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks: BlobPart[] = [];
      const startedAt = Date.now();
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = () => {
        const type = rec.mimeType || mime || "audio/webm";
        onSave({ blob: new Blob(chunks, { type }), filename: `recording${extensionFor(type)}`, durationSec: (Date.now() - startedAt) / 1000 });
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
      setError("Microphone access was blocked. Allow microphone permission in your browser and try again.");
      cleanupStream();
    }
  }

  function onFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const probe = new Audio();
    const u = URL.createObjectURL(f);
    probe.preload = "metadata";
    const done = (d: number) => { URL.revokeObjectURL(u); onSave({ blob: f, filename: f.name, durationSec: Number.isFinite(d) ? d : 0 }); };
    probe.onloadedmetadata = () => done(probe.duration);
    probe.onerror = () => done(0);
    probe.src = u;
  }

  const shownTime = recording ? elapsed : saved?.durationSec ?? 0;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* mic circle */}
      <div className={`grid h-24 w-24 place-items-center rounded-full ${saved && !recording ? "bg-ok-soft" : "bg-lav-100"} ${recording ? "recording-pulse" : ""}`}>
        {saved && !recording ? <CheckCircle2 size={40} className="text-ok" /> : <Mic size={40} className="text-lav-500" />}
      </div>

      {/* waveform bars */}
      <div className="flex h-12 w-full items-center justify-center gap-[3px]" aria-hidden>
        {Array.from({ length: BARS }).map((_, i) => {
          const idle = 0.12 + 0.55 * Math.abs(Math.sin(i * 0.55)) * Math.abs(Math.cos(i * 0.23));
          const h = recording ? Math.max(0.08, level * (0.35 + 0.65 * Math.abs(Math.sin(i * 0.8 + elapsed * 7)))) : idle;
          return <span key={i} className={`w-[3px] rounded-full ${recording ? "bg-lav-500" : saved ? "bg-ok/40" : "bg-lav-400/60"}`} style={{ height: `${Math.max(4, h * 46)}px` }} />;
        })}
      </div>
      <div className="font-mono text-sm text-ink-soft">{fmtTime(shownTime)} / {fmtTime(maxSeconds)}</div>

      {error && <p className="w-full rounded-lg bg-bad-soft px-3 py-2 text-xs text-bad">{error}</p>}

      {recording ? (
        <button className="btn-primary w-full bg-bad hover:bg-red-700" onClick={stop}><Square size={15} /> Stop Recording</button>
      ) : saved ? (
        <div className="w-full space-y-2">
          {url && <audio controls src={url} className="h-10 w-full" />}
          <button className="btn-ghost w-full" onClick={onClear} disabled={disabled}><RotateCcw size={15} /> Record again</button>
        </div>
      ) : (
        <div className="flex w-full gap-2">
          <button className="btn-primary flex-1 py-3" onClick={start} disabled={disabled}>
            <span className="h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white/70" /> Start Recording
          </button>
          <button className="btn-ghost px-3" onClick={() => fileRef.current?.click()} disabled={disabled} title="Upload an audio file (.wav, .webm, .m4a)">
            <Upload size={16} />
          </button>
          <input ref={fileRef} type="file" accept=".wav,.webm,.ogg,.m4a,.mp3,audio/*" className="hidden" onChange={onFile} />
        </div>
      )}
    </div>
  );
}
