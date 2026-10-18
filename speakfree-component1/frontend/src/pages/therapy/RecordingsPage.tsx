/**
 * RecordingsPage – every therapy practice recording kept in this browser, grouped by exercise,
 * so the learner can hear how their speech changes over time. Nothing here is uploaded.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Headphones, ShieldCheck, Trash2 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { Card, Spinner } from "../../components/ui";
import RecordingList from "../../components/therapy/RecordingList";
import { practiceRecordings, type PracticeRecording } from "../../utils/practiceRecordings";
import { TYPE_LABEL } from "./labels";

export default function RecordingsPage() {
  const { activePatient } = useAuth();
  const [items, setItems] = useState<PracticeRecording[] | null>(null);
  const [type, setType] = useState("all");
  const [confirmAll, setConfirmAll] = useState(false);
  const load = useCallback(() => { if (activePatient) void practiceRecordings.list(activePatient.id).then(setItems); }, [activePatient]);
  useEffect(() => { setItems(null); load(); }, [load]);

  const types = useMemo(() => [...new Set((items ?? []).map((r) => r.exerciseType))], [items]);
  const shown = (items ?? []).filter((r) => type === "all" || r.exerciseType === type);
  const groups = useMemo(() => {
    const m = new Map<string, PracticeRecording[]>();
    shown.forEach((r) => m.set(r.exerciseId, [...(m.get(r.exerciseId) ?? []), r]));
    return [...m.values()];
  }, [shown]);

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (!items) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight"><Headphones className="text-navy" /> My recordings</h1>
          <p className="mt-1 text-sm text-ink-soft">{activePatient.full_name} · listen to your practice and hear how you're improving.</p>
        </div>
        {items.length > 0 && (confirmAll ? (
          <span className="flex items-center gap-2 text-sm">Delete all {items.length}?
            <button className="font-semibold text-bad hover:underline" onClick={() => void practiceRecordings.removeAll(activePatient.id).then(() => { setConfirmAll(false); load(); })}>Yes, delete</button>
            <button className="muted hover:underline" onClick={() => setConfirmAll(false)}>Cancel</button>
          </span>
        ) : <button className="btn-ghost py-2" onClick={() => setConfirmAll(true)}><Trash2 size={15} /> Delete all</button>)}
      </div>

      <p className="flex items-center gap-2 rounded-xl bg-lav-50 p-3 text-sm text-ink"><ShieldCheck size={16} className="shrink-0 text-lav-600" />
        Your recordings are saved only in this browser on this device. They are never uploaded – clearing your browser data removes them.</p>

      {types.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {["all", ...types].map((t) => (
            <button key={t} onClick={() => setType(t)} className={`chip ${type === t ? "bg-navy text-white" : "bg-white text-ink-soft ring-1 ring-line hover:bg-lav-50"}`}>
              {t === "all" ? `All (${items.length})` : TYPE_LABEL[t] ?? t}
            </button>
          ))}
        </div>
      )}

      {groups.length === 0 ? (
        <Card><RecordingList items={[]} onDelete={() => undefined} /><Link to="/therapy-plan" className="btn-primary mt-4">Go to my therapy plan</Link></Card>
      ) : groups.map((g) => (
        <Card key={g[0].exerciseId} title={g[0].exerciseTitle}
          right={<span className="flex items-center gap-3 text-xs muted">{g.length} recording{g.length === 1 ? "" : "s"}
            <Link to={`/therapy/exercise/${g[0].exerciseId}`} className="font-semibold text-brand hover:underline">Practise again →</Link></span>}>
          <RecordingList items={g} showTitle={false} onDelete={(id) => void practiceRecordings.remove(id).then(load)} />
        </Card>
      ))}
    </div>
  );
}
