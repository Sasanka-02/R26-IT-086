/**
 * RecordingList – the learner's own practice recordings from this browser: play, download, delete.
 * Object URLs are created per render list and revoked when the list changes or unmounts.
 */
import { useEffect, useMemo, useState } from "react";
import { Download, Mic, Trash2 } from "lucide-react";
import type { PracticeRecording } from "../../utils/practiceRecordings";
import { ScorePill } from "../progressCharts";

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;

export default function RecordingList({ items, onDelete, showTitle = true, empty }: {
  items: PracticeRecording[]; onDelete: (id: string) => void; showTitle?: boolean; empty?: string;
}) {
  const urls = useMemo(() => new Map(items.map((r) => [r.id, URL.createObjectURL(r.blob)])), [items]);
  useEffect(() => () => urls.forEach((u) => URL.revokeObjectURL(u)), [urls]);
  const [confirm, setConfirm] = useState<string | null>(null);

  if (items.length === 0) {
    return <p className="flex items-center gap-2 text-sm muted"><Mic size={15} /> {empty ?? "No recordings yet – press Start on an exercise and your voice is saved here."}</p>;
  }
  return (
    <ul className="space-y-3">
      {items.map((r) => (
        <li key={r.id} className="rounded-xl border border-line bg-white p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="min-w-0">
              {showTitle && <p className="truncate font-semibold text-ink">{r.exerciseTitle}</p>}
              <p className="text-xs muted">{new Date(r.createdAt).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} · {fmt(r.durationSec)}</p>
            </div>
            <div className="flex items-center gap-2">
              {r.score !== null && <ScorePill score={r.score} />}
              <a href={urls.get(r.id)} download={`speakfree-${r.exerciseId}-${r.createdAt.slice(0, 10)}.webm`} className="text-ink-muted hover:text-navy" aria-label="Download recording" title="Download"><Download size={16} /></a>
              {confirm === r.id ? (
                <span className="flex items-center gap-1 text-xs">
                  <button className="font-semibold text-bad hover:underline" onClick={() => { onDelete(r.id); setConfirm(null); }}>Delete</button>
                  <button className="muted hover:underline" onClick={() => setConfirm(null)}>Cancel</button>
                </span>
              ) : (
                <button className="text-ink-muted hover:text-bad" onClick={() => setConfirm(r.id)} aria-label="Delete recording" title="Delete"><Trash2 size={16} /></button>
              )}
            </div>
          </div>
          <audio controls preload="metadata" src={urls.get(r.id)} className="h-9 w-full" />
        </li>
      ))}
    </ul>
  );
}
