/**
 * Patient practice charts (Component 4 dashboard) – dependency-free SVG/HTML in the SpeakFree palette.
 * Single-series charts use navy; the one two-series chart (first try vs latest) uses
 * lavender #7C6CF0 → teal #0E9F8E (validated: CVD ΔE 18.6, contrast ≥ 3:1 on white) and is
 * always direct-labelled with a legend. Every mark has a hover tooltip; text stays in ink tokens.
 */
import { useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { COLORS } from "./ui";
import type { Dashboard, ProgressSummary } from "../types/integration";

export const FIRST_COLOR = "#7C6CF0";
export const LATEST_COLOR = "#0E9F8E";
const GRID = "#EEF0F7";

export function EmptyChart({ message }: { message: string }) {
  return <div className="grid min-h-[150px] place-items-center rounded-xl border border-dashed border-line px-6 text-center text-sm muted">{message}</div>;
}

function Tip({ children, left }: { children: ReactNode; left: number }) {
  return (
    <div className="pointer-events-none absolute -top-2 z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-lift"
      style={{ left: `${Math.max(12, Math.min(88, left))}%` }}>
      {children}
    </div>
  );
}

/** One headline number with an icon and a caption. */
export function KpiTile({ icon: Icon, value, label, caption }: { icon: LucideIcon; value: ReactNode; label: string; caption?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-lav-100 text-navy"><Icon size={19} /></span>
      <div className="mt-3 text-2xl font-extrabold tabular-nums text-ink">{value}</div>
      <div className="text-sm font-medium text-ink-soft">{label}</div>
      {caption && <div className="mt-0.5 text-xs muted">{caption}</div>}
    </div>
  );
}

/** Score chip toned by band (colour + the number itself, never colour alone). */
export function ScorePill({ score }: { score: number }) {
  const tone = score >= 75 ? "bg-ok-soft text-ok" : score >= 45 ? "bg-warn-soft text-warn" : "bg-bad-soft text-bad";
  return <span className={`inline-flex min-w-[2.75rem] justify-center rounded-md px-2 py-0.5 text-xs font-bold tabular-nums ${tone}`}>{score}</span>;
}

/** Vertical columns on a recessive track (counts per period), hover for details. */
function Columns({ data, height = 170 }: {
  data: { key: string; label: string; value: number; tip: ReactNode }[]; height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="relative">
      <div className="flex items-end gap-[2px]" style={{ height }} onMouseLeave={() => setHover(null)}>
        {data.map((d, i) => (
          <div key={d.key} className="flex h-full flex-1 cursor-default flex-col justify-end px-[3px]" onMouseEnter={() => setHover(i)}>
            <div className="relative w-full flex-1 rounded-md" style={{ background: GRID }}>
              <div className="absolute inset-x-0 bottom-0 rounded-md transition-[height] duration-500"
                style={{ height: `${(d.value / max) * 100}%`, background: hover === i ? COLORS.brand : COLORS.navy, minHeight: d.value ? 4 : 0 }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-[2px] text-center text-[11px] muted">
        {data.map((d) => <span key={d.key} className="flex-1 truncate">{d.label}</span>)}
      </div>
      {hover !== null && <Tip left={((hover + 0.5) / data.length) * 100}>{data[hover].tip}</Tip>}
    </div>
  );
}

/** Exercises per day, last 14 days. */
export function DailyActivityChart({ daily, height }: { daily: ProgressSummary["daily"]; height?: number }) {
  if (daily.every((d) => d.sessions === 0)) return <EmptyChart message="No practice in the last two weeks yet." />;
  return (
    <Columns height={height} data={daily.map((d) => {
      const day = new Date(`${d.date}T00:00:00`);
      return {
        key: d.date, label: day.toLocaleDateString(undefined, { weekday: "narrow" }), value: d.sessions,
        tip: <><b className="text-ink">{day.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}</b>
          <div className="muted">{d.sessions} exercise{d.sessions === 1 ? "" : "s"}{d.average_score !== null ? ` · average ${d.average_score}` : ""}</div></>,
      };
    })} />
  );
}

/** Exercises per week, oldest → newest. */
export function WeeklyColumns({ weekly, height }: { weekly: Dashboard["weekly"]; height?: number }) {
  const data = [...weekly].reverse();
  if (data.every((w) => w.sessions === 0)) return <EmptyChart message="No practice in the last four weeks." />;
  return (
    <Columns height={height} data={data.map((w) => ({
      key: w.label, label: w.label, value: w.sessions,
      tip: <><b className="text-ink">{w.label}</b><div className="muted">{w.sessions} exercises · {w.minutes} min</div>
        <div className="muted">{w.average_score !== null ? `Average score ${w.average_score}` : "No practice"}</div></>,
    }))} />
  );
}

/** First attempt vs latest attempt per exercise – paired horizontal bars, direct-labelled. */
export function FirstVsLatestChart({ rows }: { rows: Dashboard["first_vs_latest"] }) {
  const [hover, setHover] = useState<string | null>(null);
  if (rows.length === 0) return <EmptyChart message="Repeat an exercise to compare your first try with your latest." />;
  return (
    <div>
      <div className="mb-3 flex gap-4 text-xs text-ink-soft">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: FIRST_COLOR }} /> First try</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: LATEST_COLOR }} /> Latest</span>
      </div>
      <ul className="space-y-3.5">
        {rows.slice(0, 6).map((r) => (
          <li key={r.exercise_id} onMouseEnter={() => setHover(r.exercise_id)} onMouseLeave={() => setHover(null)}
            className={`rounded-lg px-1 transition ${hover === r.exercise_id ? "bg-canvas" : ""}`}
            title={`${r.title}: first ${r.first_score} → latest ${r.latest_score} over ${r.attempts} tries`}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
              <span className="truncate font-medium text-ink">{r.title.split(" - ").pop()}</span>
              <span className={`shrink-0 text-xs font-bold ${r.change > 0 ? "text-ok" : r.change < 0 ? "text-warn" : "text-ink-soft"}`}>
                {r.change > 0 ? "+" : ""}{r.change} pts · {r.attempts} tries
              </span>
            </div>
            {[["First", r.first_score, FIRST_COLOR], ["Latest", r.latest_score, LATEST_COLOR]].map(([label, v, c]) => (
              <div key={label as string} className="mt-[2px] flex items-center gap-2">
                <div className="h-2.5 flex-1 rounded-full" style={{ background: GRID }}>
                  <div className="h-2.5 rounded-full" style={{ width: `${Math.max(2, v as number)}%`, background: c as string }} />
                </div>
                <span className="w-7 text-right font-mono text-[11px] text-ink">{v}</span>
              </div>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}
