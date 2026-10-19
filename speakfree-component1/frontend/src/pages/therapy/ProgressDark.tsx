/**
 * ProgressDark – the light-theme "My progress" dashboard (Component 4).
 *
 * Plain language first: report card → level ladder + timeline → highlights + goals; then the numbers:
 * KPI tiles, score trend (area), average-score gauge, weekly practice, daily activity, practice mix,
 * first try vs latest, score by exercise type, badges, recent exercises and a week-by-week table.
 *
 * Colour (on the white #FFFFFF card surface with the dataviz validator):
 *   single series  brand blue #1D4ED8 · crosshair amber #D97706
 *   first vs latest  blue #3987E5 → aqua #199E70        (CVD ΔE 19.6, contrast ≥ 3:1)
 *   exercise types   8-slot categorical, fixed per plan  (worst adjacent CVD ΔE 8.4, contrast ≥ 3:1)
 * Every multi-series chart has a legend with direct numbers; text always uses the ink tokens.
 */
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowDown, ArrowRight, ArrowUp, Award, BookOpenCheck, CalendarCheck, CalendarDays, CheckCircle2, Circle, Clock, Compass, Crown, Flag, Flame,
  Footprints, LifeBuoy, Lightbulb, Lock, Minus, Mountain, Sparkles, Star, Target, TrendingUp, UserCheck, UserCog, Zap, type LucideIcon,
} from "lucide-react";
import type { Badge, Goal, LevelEvent, ReportStatus, TherapyPlan } from "../../types/integration";
import { TYPE_LABEL } from "./labels";

// --------------------------------------------------------------------------- light tokens
export const D = {
  page: "#F5F6FB", card: "#FFFFFF", line: "#E6E8F2", track: "#EEF0F7",
  ink: "#1B2559", soft: "#4A5578", muted: "#7A8299",
  accent: "#1D4ED8", cross: "#D97706", first: "#3987E5", latest: "#199E70",
};
const SLOTS = ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#008300", "#9085E9", "#DC2626"];
const OTHER = "#9AA1B5";
const TYPE_ORDER = ["reading", "pacing", "daf", "picture", "conversation", "roleplay", "words", "sound_drill", "clear_speech", "loudness", "sustained_vowel"];
const TONE = { gold: "#D97706", mint: "#0D9488", pink: "#DB2777", blue: "#1D4ED8" };

/** Colour follows the exercise type: slots are given in a fixed type order to the types in this plan. */
function useTypeColors(plan: TherapyPlan) {
  return useMemo(() => {
    const present = new Set([...plan.library.map((e) => e.type), ...plan.progress.by_type.map((t) => t.type)]);
    const ordered = TYPE_ORDER.filter((t) => present.has(t));
    const map: Record<string, string> = {};
    ordered.forEach((t, i) => { map[t] = i < SLOTS.length ? SLOTS[i] : OTHER; });
    return (t: string) => map[t] ?? OTHER;
  }, [plan]);
}

// --------------------------------------------------------------------------- primitives
export function DCard({ title, subtitle, right, children, className = "" }: {
  title?: string; subtitle?: string; right?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-2xl border p-5 ${className}`} style={{ background: D.card, borderColor: D.line }}>
      {(title || right) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-bold" style={{ color: D.ink }}>{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs" style={{ color: D.muted }}>{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

function Empty({ message }: { message: string }) {
  return <div className="grid min-h-[160px] place-items-center rounded-xl border border-dashed px-6 text-center text-sm" style={{ borderColor: D.line, color: D.muted }}>{message}</div>;
}

function TipBox({ title, lines, style }: { title: string; lines: string[]; style?: React.CSSProperties }) {
  return (
    <div className="pointer-events-none absolute z-10 whitespace-nowrap rounded-lg border px-3 py-2 text-xs shadow-xl" style={{ background: "#FFFFFF", borderColor: D.line, ...style }}>
      <p className="font-semibold" style={{ color: D.ink }}>{title}</p>
      {lines.map((l) => <p key={l} className="mt-0.5" style={{ color: D.soft }}>{l}</p>)}
    </div>
  );
}

function Meter({ value, color = D.accent }: { value: number; color?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: D.track }}>
      <div className="h-full rounded-full" style={{ width: `${Math.max(2, Math.min(100, value))}%`, background: color }} />
    </div>
  );
}

function Pill({ score }: { score: number }) {
  const c = score >= 65 ? D.accent : score >= 45 ? D.cross : "#DC2626";
  return <span className="inline-flex min-w-[3rem] justify-center rounded-md border px-2 py-0.5 text-xs font-bold tabular-nums" style={{ color: c, borderColor: `${c}80`, background: `${c}14` }}>{score}</span>;
}

function Kpi({ icon: Icon, tone, value, label, caption }: { icon: LucideIcon; tone: keyof typeof TONE; value: ReactNode; label: string; caption?: string }) {
  const c = TONE[tone];
  return (
    <div className="rounded-2xl border p-4" style={{ background: D.card, borderColor: D.line }}>
      <span className="grid h-10 w-10 place-items-center rounded-xl border" style={{ color: c, borderColor: `${c}55` }}><Icon size={19} /></span>
      <p className="mt-4 text-2xl font-bold tabular-nums" style={{ color: D.ink }}>{value}</p>
      <p className="mt-0.5 text-sm" style={{ color: D.ink }}>{label}</p>
      {caption && <p className="mt-1 text-xs" style={{ color: c }}>{caption}</p>}
    </div>
  );
}

// --------------------------------------------------------------------------- charts
/** Smooth path through points (Catmull-Rom → cubic Bézier). */
function smooth(pts: [number, number][]) {
  if (pts.length < 2) return "";
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i - 1] ?? pts[i];
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[i + 1];
    const [x3, y3] = pts[i + 2] ?? pts[i + 1];
    d += ` C${x1 + (x2 - x0) / 6},${y1 + (y2 - y0) / 6} ${x2 - (x3 - x1) / 6},${y2 - (y3 - y1) / 6} ${x2},${y2}`;
  }
  return d;
}

/** Score of every attempt – area under a 2px line, dashed "Strong" reference, crosshair + tooltip. */
export function ScoreTrendArea({ history, strong, height = 260 }: {
  history: TherapyPlan["progress"]["history"]; strong: number; height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  if (history.length < 2) return <Empty message="Complete two or more exercises to see your score trend." />;
  const W = 760, H = height, L = 40, R = 14, T = 12, B = 28;
  const x = (i: number) => L + (i / (history.length - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - v / 100) * (H - T - B);
  const pts = history.map((h, i) => [x(i), y(h.score)] as [number, number]);
  const line = smooth(pts);
  const step = Math.max(1, Math.ceil(history.length / 18));
  const h = hover !== null ? history[hover] : null;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Score on each attempt"
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const px = ((e.clientX - r.left) / r.width) * W;
          setHover(Math.max(0, Math.min(history.length - 1, Math.round(((px - L) / (W - L - R)) * (history.length - 1)))));
        }}>
        <defs>
          <linearGradient id="dkScoreFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={D.accent} stopOpacity={0.18} /><stop offset="100%" stopColor={D.accent} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={D.line} /><text x={L - 8} y={y(v) + 4} textAnchor="end" fontSize={11} fill={D.muted}>{v}</text></g>
        ))}
        <line x1={L} x2={W - R} y1={y(strong)} y2={y(strong)} stroke={D.muted} strokeOpacity={0.6} strokeDasharray="4 4" />
        <text x={W - R - 4} y={y(strong) + 14} textAnchor="end" fontSize={10} fill={D.muted}>Strong</text>
        <path d={`${line} L${pts[pts.length - 1][0]},${y(0)} L${pts[0][0]},${y(0)} Z`} fill="url(#dkScoreFill)" />
        <path d={line} fill="none" stroke={D.accent} strokeWidth={2} />
        {history.map((p, i) => i % step === 0 || i === history.length - 1 ? (
          <text key={i} x={x(i)} y={H - 8} textAnchor="middle" fontSize={11} fill={D.muted}>#{p.attempt}</text>
        ) : null)}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={T} y2={y(0)} stroke={D.cross} strokeDasharray="3 3" />
            <circle cx={x(hover)} cy={y(history[hover].score)} r={5} fill={D.cross} stroke={D.card} strokeWidth={2} />
          </g>
        )}
      </svg>
      {h && (
        <TipBox title={`Score ${h.score}`} lines={[h.title, `Attempt #${h.attempt} · ${new Date(h.completed_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}`]}
          style={{ top: 0, left: `${Math.min(68, (x(hover!) / W) * 100)}%` }} />
      )}
    </div>
  );
}

/** Semicircle gauge for one 0–100 headline value. */
export function ScoreGauge({ value, label }: { value: number | null; label: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const r = 80, cx = 100, cy = 96;
  const a = Math.PI * (1 - v / 100);
  const end = { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) };
  return (
    <figure className="mx-auto w-full max-w-[240px]">
      <svg viewBox="0 0 200 110" role="img" aria-label={`${label}: ${value ?? "no data"} out of 100`}>
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke={D.track} strokeWidth={20} strokeLinecap="round" />
        {value !== null && v > 0 && <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`} fill="none" stroke={D.accent} strokeWidth={20} strokeLinecap="round" />}
        <text x={cx} y={cy - 8} textAnchor="middle" fontSize="32" fontWeight="700" fill={D.ink}>{value ?? "–"}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" fontSize="11" fill={D.muted}>out of 100</text>
      </svg>
    </figure>
  );
}

/** Vertical bars with a y-axis and gridlines; per-bar hover tooltip. */
function BarsAxis({ data, height = 220, track = false, axis = true }: {
  data: { key: string; label: string; value: number; tip: string[]; title: string }[]; height?: number; track?: boolean; axis?: boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 400, H = height, L = axis ? 30 : 4, R = 4, T = 10, B = 24;
  const rawMax = Math.max(1, ...data.map((d) => d.value));
  const max = axis ? Math.ceil(rawMax / 2) * 2 : rawMax;
  const ticks = axis ? Array.from({ length: 5 }, (_, i) => Math.round((max / 4) * i)) : [];
  const slot = (W - L - R) / data.length;
  const bw = Math.min(44, slot * (track ? 0.45 : 0.6));
  const y = (v: number) => T + (1 - v / max) * (H - T - B);
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}><line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke={D.line} /><text x={L - 6} y={y(t) + 4} textAnchor="end" fontSize={11} fill={D.muted}>{t}</text></g>
        ))}
        {data.map((d, i) => {
          const cx = L + slot * i + slot / 2;
          const top = y(d.value);
          return (
            <g key={d.key} onMouseEnter={() => setHover(i)}>
              <rect x={L + slot * i} y={T} width={slot} height={H - T - B} fill="transparent" />
              {track && <rect x={cx - bw / 2} y={T} width={bw} height={H - T - B} rx={bw / 2} fill={D.track} />}
              {d.value > 0 && <rect x={cx - bw / 2} y={top} width={bw} height={y(0) - top} rx={track ? bw / 2 : 4} fill={hover === i ? "#5B7FE8" : D.accent} />}
              <text x={cx} y={H - 6} textAnchor="middle" fontSize={11} fill={D.muted}>{d.label}</text>
            </g>
          );
        })}
      </svg>
      {hover !== null && <TipBox title={data[hover].title} lines={data[hover].tip}
        style={{ top: 0, left: `${Math.min(62, ((L + slot * hover) / W) * 100)}%` }} />}
    </div>
  );
}

function WeeklyPractice({ weekly }: { weekly: TherapyPlan["dashboard"]["weekly"] }) {
  const data = [...weekly].reverse();
  if (data.every((w) => w.sessions === 0)) return <Empty message="No practice in the last four weeks." />;
  return <BarsAxis data={data.map((w) => ({
    key: w.label, label: w.label.replace(" weeks ago", "w ago"), value: w.sessions, title: w.label,
    tip: [`${w.sessions} exercise${w.sessions === 1 ? "" : "s"} · ${w.minutes} min`, w.average_score !== null ? `Average score ${w.average_score}` : "No practice"],
  }))} />;
}

function DailyActivity({ daily }: { daily: TherapyPlan["progress"]["daily"] }) {
  if (daily.every((d) => d.sessions === 0)) return <Empty message="No practice in the last two weeks yet." />;
  return <BarsAxis track axis={false} data={daily.map((d) => {
    const day = new Date(`${d.date}T00:00:00`);
    return {
      key: d.date, label: day.toLocaleDateString(undefined, { weekday: "narrow" }), value: d.sessions,
      title: day.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }),
      tip: [`${d.sessions} exercise${d.sessions === 1 ? "" : "s"}`, d.average_score !== null ? `Average score ${d.average_score}` : "No practice"],
    };
  })} />;
}

/** Share of exercises by type – donut with a 2px surface gap, legend carries the numbers. */
function PracticeMix({ byType, color }: { byType: TherapyPlan["progress"]["by_type"]; color: (t: string) => string }) {
  const [hover, setHover] = useState<string | null>(null);
  if (byType.length === 0) return <Empty message="No exercises yet." />;
  const total = byType.reduce((n, t) => n + t.attempts, 0);
  const rows = [...byType].sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type));
  const R = 80, r = 52, C = 90;
  let angle = -Math.PI / 2;
  const arcs = rows.map((t) => {
    const sweep = (t.attempts / total) * Math.PI * 2;
    const a0 = angle, a1 = angle + sweep;
    angle = a1;
    const p = (rad: number, a: number) => `${C + rad * Math.cos(a)},${C + rad * Math.sin(a)}`;
    const large = sweep > Math.PI ? 1 : 0;
    const d = rows.length === 1
      ? `M${C - R},${C} A${R},${R} 0 1 1 ${C + R},${C} A${R},${R} 0 1 1 ${C - R},${C} M${C - r},${C} A${r},${r} 0 1 0 ${C + r},${C} A${r},${r} 0 1 0 ${C - r},${C}Z`
      : `M${p(R, a0)} A${R},${R} 0 ${large} 1 ${p(R, a1)} L${p(r, a1)} A${r},${r} 0 ${large} 0 ${p(r, a0)}Z`;
    return { t, d };
  });
  const h = rows.find((t) => t.type === hover);
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="relative h-[180px] w-[180px] shrink-0">
        <svg viewBox="0 0 180 180" className="h-full w-full" role="img" aria-label="Practice mix by exercise type" onMouseLeave={() => setHover(null)}>
          {arcs.map(({ t, d }) => (
            <path key={t.type} d={d} fill={color(t.type)} stroke={D.card} strokeWidth={2} fillRule="evenodd"
              opacity={hover && hover !== t.type ? 0.45 : 1} onMouseEnter={() => setHover(t.type)} />
          ))}
          <text x={C} y={C - 2} textAnchor="middle" fontSize="22" fontWeight="700" fill={D.ink}>{total}</text>
          <text x={C} y={C + 14} textAnchor="middle" fontSize="10" fill={D.muted}>exercises</text>
        </svg>
        {h && <TipBox title={TYPE_LABEL[h.type] ?? h.label} lines={[`${h.attempts} of ${total} exercises`, `Average score ${h.average_score ?? "–"}`]} style={{ top: -8, left: 120 }} />}
      </div>
      <ul className="w-full space-y-2 text-sm">
        {rows.map((t) => (
          <li key={t.type} className="flex items-center gap-2" onMouseEnter={() => setHover(t.type)} onMouseLeave={() => setHover(null)}>
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: color(t.type) }} />
            <span className="flex-1" style={{ color: D.ink }}>{t.label}</span>
            <span className="tabular-nums" style={{ color: D.soft }}>{Math.round((t.attempts / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** First attempt vs latest per exercise – paired horizontal bars on a 0–100 axis, with legend. */
function FirstVsLatest({ rows }: { rows: TherapyPlan["dashboard"]["first_vs_latest"] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (rows.length === 0) return <Empty message="Repeat an exercise to compare your first try with your latest." />;
  const data = rows.slice(0, 6);
  const W = 900, L = 170, R = 20, T = 6, rowH = 56, H = T + data.length * rowH + 30;
  const x = (v: number) => L + (v / 100) * (W - L - R);
  const short = (t: string) => { const s = t.split(" - ").pop() ?? t; return s.length > 22 ? `${s.slice(0, 21)}…` : s; };
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="First try against latest score per exercise" onMouseLeave={() => setHover(null)}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}><line x1={x(v)} x2={x(v)} y1={T} y2={H - 26} stroke={D.line} /><text x={x(v)} y={H - 8} textAnchor="middle" fontSize={12} fill={D.muted}>{v}</text></g>
        ))}
        {data.map((r, i) => {
          const top = T + i * rowH + 12;
          return (
            <g key={r.exercise_id} onMouseEnter={() => setHover(i)}>
              <rect x={0} y={top - 10} width={W} height={rowH - 4} fill="transparent" />
              <text x={L - 10} y={top + 15} textAnchor="end" fontSize={13} fill={D.ink}>{short(r.title)}</text>
              <rect x={L} y={top} width={Math.max(2, x(r.first_score) - L)} height={13} rx={4} fill={D.first} />
              <rect x={L} y={top + 15} width={Math.max(2, x(r.latest_score) - L)} height={13} rx={4} fill={D.latest} />
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-center gap-4 text-xs" style={{ color: D.soft }}>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: D.first }} /> First try</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: D.latest }} /> Latest</span>
      </div>
      {hover !== null && <TipBox title={data[hover].title}
        lines={[`First try ${data[hover].first_score} → latest ${data[hover].latest_score}`, `${data[hover].change >= 0 ? "+" : ""}${data[hover].change} points over ${data[hover].attempts} tries`]}
        style={{ top: T + hover * rowH, left: "40%" }} />}
    </div>
  );
}

// --------------------------------------------------------------------------- cards
const LIGHT: Record<ReportStatus, { dot: string; icon: LucideIcon }> = {
  improving: { dot: D.accent, icon: TrendingUp }, steady: { dot: D.cross, icon: Minus }, needs_support: { dot: "#DC2626", icon: LifeBuoy },
};

function ReportCardDark({ card }: { card: TherapyPlan["dashboard"]["report_card"] }) {
  const tone = LIGHT[card.status];
  const Icon = tone.icon;
  return (
    <section className="rounded-2xl border p-5 sm:p-6" style={{ background: D.card, borderColor: D.line }} aria-label="Progress report">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex flex-col gap-1.5 rounded-full p-2" style={{ background: D.page }} aria-hidden>
          {(["improving", "steady", "needs_support"] as ReportStatus[]).map((s) => (
            <span key={s} className="h-4 w-4 rounded-full" style={{ background: s === card.status ? LIGHT[s].dot : D.line }} />
          ))}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: D.muted }}>Your progress report</p>
          <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold"
            style={{ color: tone.dot, borderColor: `${tone.dot}66`, background: `${tone.dot}1A` }}><Icon size={15} /> {card.label}</span>
          <p className="mt-3 text-xl font-bold leading-snug" style={{ color: D.ink }}>{card.headline}</p>
        </div>
      </div>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2">
        {[["This week", card.this_week, CalendarDays], ["Next step", card.next_step, ArrowRight]].map(([t, v, I]) => {
          const Ico = I as LucideIcon;
          return (
            <div key={t as string} className="rounded-xl px-4 py-3" style={{ background: D.page }}>
              <dt className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: D.soft }}><Ico size={14} /> {t as string}</dt>
              <dd className="mt-1 text-sm" style={{ color: D.ink }}>{v as string}</dd>
            </div>
          );
        })}
      </dl>
      {card.reasons.length > 0 && (
        <div className="mt-4 text-sm">
          <p className="text-xs font-semibold" style={{ color: D.soft }}>Why “{card.label.toLowerCase()}”</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5" style={{ color: D.ink }}>{card.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      )}
    </section>
  );
}

const EVENT_ICON: Record<string, LucideIcon> = { up: ArrowUp, down: ArrowDown, mastered: Flag, therapist: UserCog, start: ArrowRight };

function Timeline({ history }: { history: LevelEvent[] }) {
  const moves = history.filter((e) => e.direction !== "start");
  if (moves.length === 0) return <p className="text-sm" style={{ color: D.muted }}>No level changes yet. Two strong attempts in a row move you up.</p>;
  return (
    <ol className="space-y-3">
      {[...moves].reverse().map((e, i) => {
        const Ico = EVENT_ICON[e.direction] ?? ArrowRight;
        const c = e.direction === "down" ? D.cross : D.accent;
        return (
          <li key={i} className="flex gap-3 text-sm">
            <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full" style={{ background: `${c}26`, color: c }}><Ico size={14} /></span>
            <span>
              <span className="font-medium" style={{ color: D.ink }}>{e.from ? `${e.from} → ${e.to}` : e.to}{e.at ? ` on ${new Date(e.at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}` : ""}</span>
              <span className="block text-xs" style={{ color: D.muted }}>{e.reason.charAt(0).toUpperCase() + e.reason.slice(1)}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function Steps({ steps }: { steps: { label: string; state: "done" | "current" | "locked" }[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((s, i) => (
        <li key={s.label} className="flex items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-semibold"
            style={s.state === "current" ? { background: D.accent, color: "#FFFFFF" } : s.state === "done" ? { background: `${D.accent}26`, color: D.accent } : { border: `1px dashed ${D.line}`, color: D.muted }}>
            {s.state === "done" ? <CheckCircle2 size={17} /> : s.state === "locked" ? <Lock size={14} /> : i + 1}
          </span>
          <div>
            <p className="text-sm font-medium" style={{ color: s.state === "locked" ? D.muted : D.ink }}>{s.label}</p>
            <p className="text-xs" style={{ color: D.muted }}>{s.state === "done" ? "Completed" : s.state === "current" ? "You are here" : "Locked"}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function LevelCard({ plan }: { plan: TherapyPlan }) {
  const { level, skill_level: skill } = plan;
  const steps = Array.from({ length: level.max_bracket - level.min_bracket + 1 }, (_, i) => {
    const b = level.min_bracket + i;
    const state = b < level.bracket || (b === level.bracket && level.mastered) ? "done" : b === level.bracket ? "current" : "locked";
    return { label: `Level ${b}${b === level.age_bracket ? " · your age" : ""}`, state } as const;
  });
  return (
    <DCard title="Practice level" subtitle={level.progress_text}>
      <Steps steps={steps} />
      {skill && (
        <div className="mt-5 border-t pt-4" style={{ borderColor: D.line }}>
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: D.muted }}>Skill steps · {TYPE_LABEL[plan.focus.ladder_type]}</p>
          <Steps steps={["Beginner", "Intermediate", "Advanced (final stage)"].map((l, i) => ({
            label: l, state: i < skill.level_index || (i === skill.level_index && skill.mastered) ? "done" : i === skill.level_index ? "current" : "locked",
          }))} />
        </div>
      )}
      <div className="mt-5 border-t pt-4" style={{ borderColor: D.line }}>
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: D.muted }}>Level timeline</p>
        <Timeline history={[...level.history, ...(skill?.history ?? [])].sort((a, b) => (a.at ?? "").localeCompare(b.at ?? ""))} />
      </div>
    </DCard>
  );
}

function WordLadderDark({ words }: { words: NonNullable<TherapyPlan["word_level"]> }) {
  return (
    <DCard title="Word practice" subtitle={words.progress_text}>
      <ol className="flex flex-wrap gap-1.5" aria-label="Word ladder">
        {Array.from({ length: words.ladder_size }, (_, i) => {
          const step = i + 1;
          const done = step < words.level || (words.mastered && step === words.level);
          const cur = step === words.level && !words.mastered;
          return (
            <li key={step} className="grid h-9 min-w-[2.25rem] place-items-center rounded-full px-2 text-sm font-semibold"
              style={cur ? { background: D.cross, color: "#FFFFFF" } : done ? { background: `${D.cross}33`, color: D.cross } : { border: `1px dashed ${D.line}`, color: D.muted }}>
              {done ? "⭐" : step <= words.word_levels ? step : `P${step - words.word_levels}`}
            </li>
          );
        })}
      </ol>
      <p className="mt-2 text-xs" style={{ color: D.muted }}>Levels 1–7 are single words; P1–P3 are phrases, sentences and tongue twisters. {words.rounds} round{words.rounds === 1 ? "" : "s"} so far.</p>
    </DCard>
  );
}

function GoalsDark({ goals }: { goals: Goal[] }) {
  return (
    <DCard title="Your goals">
      <ul className="space-y-2">
        {goals.map((g) => (
          <li key={g.id} className="flex items-start gap-2.5 rounded-xl px-4 py-3 text-sm" style={{ background: D.page }}>
            {g.met ? <CheckCircle2 size={18} className="mt-0.5 shrink-0" style={{ color: D.accent }} /> : <Circle size={18} className="mt-0.5 shrink-0" style={{ color: D.muted }} />}
            <span>
              <span className="font-medium" style={{ color: D.ink }}>{g.text}</span>
              {g.source === "therapist" && <span className="ml-2 inline-flex items-center gap-1 text-[11px]" style={{ color: D.accent }}><UserCheck size={11} /> therapist</span>}
              <span className="block text-xs" style={{ color: D.muted }}>Now: {g.current ?? "no data yet"} · {g.met ? "Goal met" : "Not met yet"}</span>
            </span>
          </li>
        ))}
      </ul>
    </DCard>
  );
}

const BADGE_STYLE: Record<string, { icon: LucideIcon; from: string; to: string }> = {
  first_step: { icon: Footprints, from: "#A8DED6", to: "#4FA897" }, ten_sessions: { icon: Award, from: "#F5B05E", to: "#C9782A" },
  streak_3: { icon: Flame, from: "#F7A072", to: "#D0561F" }, streak_7: { icon: Zap, from: "#FFD36E", to: "#D79A16" },
  score_90: { icon: Star, from: "#F0C6E6", to: "#C4508F" }, level_up: { icon: Mountain, from: "#8EC3F5", to: "#3F87DD" },
  top_level: { icon: Crown, from: "#C9B6F7", to: "#7C5FD6" }, explorer: { icon: Compass, from: "#9FE3EA", to: "#2B97A6" },
  first_words: { icon: Sparkles, from: "#A8E6B8", to: "#2E9E5B" }, word_master: { icon: BookOpenCheck, from: "#A8E6B8", to: "#2E9E5B" },
};

function Medal({ badge, size = 52 }: { badge: Badge; size?: number }) {
  const s = BADGE_STYLE[badge.id] ?? BADGE_STYLE.first_step;
  const Icon = badge.earned ? s.icon : Lock;
  return (
    <div className="grid shrink-0 place-items-center rounded-2xl" style={{
      width: size, height: size,
      background: badge.earned ? `linear-gradient(145deg, ${s.from}, ${s.to})` : D.page,
      boxShadow: badge.earned ? `0 10px 24px -10px ${s.to}` : undefined, border: badge.earned ? undefined : `1px dashed ${D.line}`,
    }}>
      <Icon size={size * 0.42} strokeWidth={2.2} style={{ color: badge.earned ? "#FFFFFF" : D.muted }} />
    </div>
  );
}

export function BadgesDark({ badges, compact = false }: { badges: Badge[]; compact?: boolean }) {
  const earned = badges.filter((b) => b.earned);
  const ordered = [...earned, ...badges.filter((b) => !b.earned)];
  const pct = badges.length ? Math.round((earned.length / badges.length) * 100) : 0;
  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <p className="text-sm" style={{ color: D.ink }}><span className="text-xl font-bold">{earned.length}</span><span style={{ color: D.soft }}> / {badges.length} earned</span></p>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: D.track }}><div className="h-full rounded-full" style={{ width: `${pct}%`, background: D.cross }} /></div>
      </div>
      <ul className={`grid gap-3 ${compact ? "grid-cols-3 sm:grid-cols-5 lg:grid-cols-9" : "grid-cols-1 sm:grid-cols-2 xl:grid-cols-3"}`}>
        {ordered.map((b) => compact ? (
          <li key={b.id} className="flex flex-col items-center gap-2 text-center" title={b.description}>
            <Medal badge={b} /><span className="text-xs font-medium" style={{ color: b.earned ? D.ink : D.muted }}>{b.title}</span>
          </li>
        ) : (
          <li key={b.id} className="flex items-center gap-3 rounded-xl p-3" style={{ background: b.earned ? "#F7F5FF" : D.page }}>
            <Medal badge={b} size={48} />
            <div className="min-w-0">
              <p className="text-sm font-semibold" style={{ color: b.earned ? D.ink : D.soft }}>{b.title}</p>
              <p className="text-xs" style={{ color: D.muted }}>{b.description}</p>
              <p className="mt-0.5 text-[11px] font-medium" style={{ color: b.earned ? D.cross : D.muted }}>{b.earned ? "Earned" : "Locked"}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

const RATING: Record<string, string> = { easy: "Felt easy", ok: "Felt okay", hard: "Felt hard" };
const dur = (s: number) => { const t = Math.round(s); return t < 60 ? `${t} sec` : `${Math.floor(t / 60)} min ${t % 60} sec`; };

// --------------------------------------------------------------------------- page body
export default function ProgressDark({ plan }: { plan: TherapyPlan }) {
  const color = useTypeColors(plan);
  const { progress: p, dashboard: d, level } = plan;
  const week = d.weekly[0];

  return (
    <div className="space-y-5">
      <ReportCardDark card={d.report_card} />
      {plan.word_level && <WordLadderDark words={plan.word_level} />}

      <div className="grid gap-5 lg:grid-cols-2">
        <LevelCard plan={plan} />
        <div className="space-y-5">
          {d.highlights.length > 0 && (
            <DCard title="What this means for you">
              <ul className="space-y-2.5">{d.highlights.map((h) => (
                <li key={h} className="flex gap-2.5 text-sm" style={{ color: D.ink }}><Lightbulb size={16} className="mt-0.5 shrink-0" style={{ color: D.cross }} />{h}</li>
              ))}</ul>
            </DCard>
          )}
          <GoalsDark goals={plan.goals} />
        </div>
      </div>

      {!p.has_data ? (
        <DCard title="No results yet">
          <p className="text-sm" style={{ color: D.soft }}>Complete any exercise from your therapy plan and save your result. Your score trend, weekly activity, practice mix and badges will appear here as charts.</p>
          <Link to="/therapy-plan" className="mt-3 inline-flex rounded-lg px-3 py-2 text-sm font-semibold" style={{ background: D.accent, color: "#FFFFFF" }}>Open my plan</Link>
        </DCard>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi icon={CalendarCheck} tone="gold" value={p.total_sessions} label="Exercises completed" caption={week ? `${week.sessions} this week` : undefined} />
            <Kpi icon={Clock} tone="mint" value={`${p.total_minutes} min`} label="Total practice time" caption={week ? `${week.minutes} min this week` : undefined} />
            <Kpi icon={Flame} tone="pink" value={`${p.streak_days} day${p.streak_days === 1 ? "" : "s"}`} label="Current streak" caption={`${d.active_days} active days in total`} />
            <Kpi icon={Award} tone="blue" value={p.average_score ?? "–"} label="Average score" caption={`Best ${p.best_score ?? "–"} out of 100`} />
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <DCard title="Score trend" subtitle="Your score on each attempt (0–100)" className="lg:col-span-2">
              <ScoreTrendArea history={p.history} strong={level.strong_threshold} />
            </DCard>
            <DCard title="Average score" subtitle="Across every exercise">
              <ScoreGauge value={p.average_score} label="Average score" />
              <p className="mt-4 text-center text-sm" style={{ color: D.soft }}>{p.trend.detail}</p>
            </DCard>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <DCard title="Weekly practice" subtitle="Exercises per week · hover for minutes and score"><WeeklyPractice weekly={d.weekly} /></DCard>
            <DCard title="Daily activity" subtitle="Exercises per day · last 14 days"><DailyActivity daily={p.daily} /></DCard>
            <DCard title="Practice mix" subtitle="Share of exercises by type"><PracticeMix byType={p.by_type} color={color} /></DCard>
          </div>

          <DCard title="First try vs latest" subtitle="Your first attempt is your baseline — here is how far you've come">
            <FirstVsLatest rows={d.first_vs_latest} />
          </DCard>

          <div className="grid gap-5 lg:grid-cols-2">
            <DCard title="Score by exercise type" subtitle="Average score, with your best in brackets">
              <ul className="space-y-4">
                {[...p.by_type].sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type)).map((t) => (
                  <li key={t.type}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2" style={{ color: D.ink }}><span className="h-2.5 w-2.5 rounded-full" style={{ background: color(t.type) }} />{t.label}</span>
                      <span className="tabular-nums" style={{ color: D.soft }}><b style={{ color: D.ink }}>{t.average_score ?? "–"}</b> ({t.best_score}) · {t.attempts}×</span>
                    </div>
                    <Meter value={t.average_score ?? 0} color={color(t.type)} />
                  </li>
                ))}
              </ul>
            </DCard>
            <DCard title="Badges" subtitle="Milestones you've reached"><BadgesDark badges={d.badges} /></DCard>
          </div>

          <DCard title="Recent exercises">
            <ul className="divide-y" style={{ borderColor: D.line }}>
              {p.recent.map((r, i) => (
                <li key={`${r.completed_at}-${i}`} className="flex flex-wrap items-center gap-3 py-3 text-sm" style={{ borderColor: D.line }}>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium" style={{ color: D.ink }}>{r.title}</p>
                    <p className="text-xs" style={{ color: D.muted }}>
                      {new Date(r.completed_at).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} · {dur(r.duration_seconds)} · {RATING[r.self_rating]}
                    </p>
                  </div>
                  <div className="hidden w-40 sm:block"><Meter value={r.score} /></div>
                  <span className="w-28 text-right text-xs" style={{ color: D.soft }}>{r.verdict}</span>
                  <Pill score={r.score} />
                </li>
              ))}
            </ul>
          </DCard>

          <details className="rounded-2xl border p-5" style={{ background: D.card, borderColor: D.line }}>
            <summary className="cursor-pointer text-sm font-semibold" style={{ color: D.ink }}>Week by week (table view)</summary>
            <table className="mt-3 w-full text-left text-sm tabular-nums" style={{ color: D.ink }}>
              <thead className="text-xs" style={{ color: D.muted }}><tr className="border-b" style={{ borderColor: D.line }}>
                <th className="py-2 pr-3 font-medium">Week</th><th className="py-2 pr-3 font-medium">Exercises</th><th className="py-2 pr-3 font-medium">Practice time</th><th className="py-2 font-medium">Average score</th>
              </tr></thead>
              <tbody>{d.weekly.map((w) => (
                <tr key={w.label} className="border-b last:border-0" style={{ borderColor: D.line }}>
                  <td className="py-2 pr-3">{w.label}</td><td className="py-2 pr-3">{w.sessions}</td><td className="py-2 pr-3">{w.minutes} min</td><td className="py-2">{w.average_score ?? "No practice"}</td>
                </tr>
              ))}</tbody>
            </table>
          </details>
        </>
      )}
      <p className="flex items-center gap-1.5 text-xs" style={{ color: D.muted }}><Target size={13} /> Based only on the exercises you have completed with this account.</p>
    </div>
  );
}
