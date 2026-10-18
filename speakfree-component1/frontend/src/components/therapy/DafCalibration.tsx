/**
 * DAF calibration (5 trials, 50 → 300 ms). Each trial plays the voice back with that delay while the
 * patient reads a different short passage; the patient's own voice is recorded on this device only
 * (for listening back and counting), the reading speed comes from the reading time. The backend
 * picks the delay with the fewest "stuck" moments × speed deviation and saves it for next time.
 */
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Headphones, Loader2, Play, Square } from "lucide-react";
import { api } from "../../api/client";
import { ErrorBox } from "../ui";
import type { DafTrial } from "../../types/integration";

const DELAYS = [50, 100, 150, 200, 300];
export const DAF_PASSAGES = [
  { title: "The Morning Walk", text: "Every morning, Nimal walks to the shop at the end of the road. He buys fresh bread and a small bottle of milk. On the way home, he waves to his neighbours and stops to look at the flowers." },
  { title: "Rain in the Garden", text: "The rain started slowly, with a few soft drops on the leaves. Soon it was falling steadily, and the garden smelled of wet grass. The birds waited quietly under the roof until the sky cleared." },
  { title: "A Trip to the Beach", text: "On Sunday the family went to the beach. The children built a sandcastle near the water, while their parents sat under a large umbrella. Later they all shared cold drinks and watched the waves." },
  { title: "The Busy Kitchen", text: "Grandmother was cooking rice and curry for lunch. She cut the onions, washed the vegetables, and stirred the pot with a wooden spoon. The whole house was filled with a warm and spicy smell." },
  { title: "The Train Journey", text: "The train left the station just after nine. Through the window, Sara could see green hills, tea fields and small villages. She read her book for a while, then closed her eyes and listened." },
];

/** Delayed playback of the microphone + a local recording of the trial (never uploaded). */
function useDelayedVoice() {
  const ref = useRef<{ ctx: AudioContext; stream: MediaStream; rec: MediaRecorder | null; chunks: Blob[] } | null>(null);
  const [active, setActive] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(delayMs: number) {
    setError(null);
    if (url) URL.revokeObjectURL(url);
    setUrl(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ctx = new AudioContext();
      const node = ctx.createDelay(1.0);
      node.delayTime.value = delayMs / 1000;
      ctx.createMediaStreamSource(stream).connect(node);
      node.connect(ctx.destination);
      const chunks: Blob[] = [];
      const rec = typeof MediaRecorder !== "undefined" ? new MediaRecorder(stream) : null;
      if (rec) {
        rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
        rec.onstop = () => setUrl(URL.createObjectURL(new Blob(chunks, { type: rec.mimeType })));
        rec.start();
      }
      ref.current = { ctx, stream, rec, chunks };
      setActive(true);
    } catch {
      setError("Microphone access is needed for DAF. Please allow the microphone and try again.");
    }
  }
  function stop() {
    const cur = ref.current;
    if (!cur) return;
    if (cur.rec && cur.rec.state !== "inactive") cur.rec.stop();
    cur.stream.getTracks().forEach((t) => t.stop());
    void cur.ctx.close();
    ref.current = null;
    setActive(false);
  }
  useEffect(() => () => { stop(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return { start, stop, active, url, error };
}

export default function DafCalibration({ patientId, onCalibrated, onSkip }: {
  patientId: string; onCalibrated: (delayMs: number) => void; onSkip: () => void;
}) {
  const [trial, setTrial] = useState(0);
  const [trials, setTrials] = useState<DafTrial[]>([]);
  const [stuck, setStuck] = useState(0);
  const [wpm, setWpm] = useState(120);
  const [result, setResult] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startedAt = useRef(0);
  const voice = useDelayedVoice();
  const passage = DAF_PASSAGES[trial % DAF_PASSAGES.length];
  const delay = DELAYS[trial];

  function stopReading() {
    if (startedAt.current) {
      const minutes = (Date.now() - startedAt.current) / 60000;
      if (minutes > 0.08) setWpm(Math.round(passage.text.split(/\s+/).length / minutes));
      startedAt.current = 0;
    }
    voice.stop();
  }

  async function next() {
    if (voice.active) stopReading();
    const all = [...trials, { delay_ms: delay, stutter_events: stuck, speech_rate_wpm: wpm }];
    setTrials(all);
    setStuck(0);
    if (trial + 1 < DELAYS.length) { setTrial(trial + 1); return; }
    setBusy(true);
    try {
      const res = await api.therapy.calibrateDaf(patientId, all);
      setResult(res.recommended_delay_ms);
      onCalibrated(res.recommended_delay_ms);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (result !== null) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-ok/30 bg-ok-soft p-5">
        <CheckCircle2 className="text-ok" size={24} />
        <p className="text-sm text-ink"><b>Calibration complete.</b> Your best delay is <b>{result} ms</b> – it's saved for your next DAF practice.</p>
      </div>
    );
  }
  return (
    <section className="space-y-4 rounded-2xl border border-lav-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-bold text-ink">Find your best delay</h3>
        <span className="chip bg-lav-100 text-lav-600">Trial {trial + 1} of {DELAYS.length} · {delay} ms</span>
      </div>
      <ol className="grid gap-2 text-sm sm:grid-cols-4">
        {["Put on headphones", "Press Start and read the passage aloud", "Press Stop when you finish", "Listen back and count the times you got stuck"].map((s, i) => (
          <li key={s} className="flex gap-2 rounded-lg bg-canvas px-3 py-2"><span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-navy text-[11px] font-bold text-white">{i + 1}</span>{s}</li>
        ))}
      </ol>
      <div className="rounded-xl bg-canvas p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-lav-600">Passage {trial + 1} · {passage.title}</p>
        <p className="mt-2 text-lg leading-relaxed text-ink">{passage.text}</p>
      </div>
      {!voice.active ? (
        <button className="btn-primary" onClick={() => { startedAt.current = Date.now(); void voice.start(delay); }}><Play size={16} /> Start – hear your voice {delay} ms late</button>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <button className="inline-flex items-center gap-2 rounded-xl bg-bad px-4 py-2.5 text-sm font-semibold text-white" onClick={stopReading}><Square size={15} /> Stop – I've finished reading</button>
          <span className="flex items-center gap-1.5 text-sm font-medium text-navy"><Headphones size={15} /> Playing your voice back {delay} ms late…</span>
        </div>
      )}
      {voice.url && !voice.active && (
        <div className="space-y-2">
          <audio controls src={voice.url} className="w-full" />
          <p className="rounded-lg bg-canvas px-3 py-2 text-xs text-ink-soft">Count one each time you hear a <b className="text-ink">repeated sound or word</b> (“b-b-bread”), a <b className="text-ink">stretched sound</b> (“sssshop”) or a <b className="text-ink">silent block</b> before a word. Normal breathing pauses don't count. The recording stays on this device.</p>
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block"><span className="label">Times you got stuck</span>
          <input type="number" min={0} max={200} className="input" value={stuck} onChange={(e) => setStuck(Math.max(0, Number(e.target.value)))} /></label>
        <label className="block"><span className="label">Reading speed (words/min)</span>
          <input type="number" min={0} max={400} className="input" value={wpm} onChange={(e) => setWpm(Math.max(0, Number(e.target.value)))} />
          <span className="mt-1 block text-xs muted">Filled in from your reading time – change it if needed.</span></label>
      </div>
      <ErrorBox message={voice.error ?? error} />
      <div className="flex flex-wrap gap-3">
        <button className="btn-primary" disabled={busy} onClick={() => void next()}>{busy && <Loader2 className="animate-spin" size={15} />}{trial + 1 < DELAYS.length ? "Next trial" : "Finish calibration"}</button>
        <button className="btn-ghost" onClick={() => { voice.stop(); onSkip(); }}>Skip – use 150 ms</button>
      </div>
    </section>
  );
}
