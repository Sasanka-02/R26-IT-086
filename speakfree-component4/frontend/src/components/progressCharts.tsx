import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from "recharts";
import { ExerciseType, ProgressSummary } from "../types/therapy";
import { EmptyChart } from "./ui";

// Chart tokens for the dark card surface (#26262F).
export const SURFACE = "#26262F";
const GRID = "#34343F";
const AXIS_TEXT = "#9C9CAB";
const TICK = { fill: AXIS_TEXT, fontSize: 12 };
/** Single-series accent (one hue per chart; the title names the series). */
export const ACCENT = "#A8DED6";
const TRACK = "#30303B";
const CROSSHAIR = "#F5B05E";

// Categorical palette, fixed order, validated with the dataviz validator on the
// card surface (dark mode): lightness, chroma, CVD and contrast checks all pass.
export const CATEGORICAL = ["#14A085", "#D06F22", "#3F87DD", "#C4508F"];

// Colour follows the exercise type, never its rank.
export const TYPE_COLORS: Record<ExerciseType, string> = {
  reading: CATEGORICAL[0],
  pacing: CATEGORICAL[1],
  daf: CATEGORICAL[2],
  picture: CATEGORICAL[3],
  // Word practice (added later): gold, a hue distinct from the four above.
  words: "#C9A227",
};

function TooltipCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg border border-snow/10 bg-shell px-3 py-2 text-xs shadow-xl">
      <p className="font-semibold text-ink">{title}</p>
      {lines.map((line) => (
        <p key={line} className="mt-0.5 text-ink-soft">
          {line}
        </p>
      ))}
    </div>
  );
}

const shortDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });

type History = ProgressSummary["history"];

/** Score of every attempt, in order — area under a 2px line, crosshair on hover. */
export function ScoreTrendChart({ history, height = 260 }: { history: History; height?: number }) {
  if (history.length < 2) {
    return <EmptyChart message="Complete two or more exercises to see your score trend." />;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={history} margin={{ top: 12, right: 8, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ACCENT} stopOpacity={0.45} />
            <stop offset="100%" stopColor={ACCENT} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis
          dataKey="attempt"
          tick={TICK}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `#${v}`}
          minTickGap={18}
        />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={TICK} tickLine={false} axisLine={false} width={40} />
        <ReferenceLine
          y={65}
          stroke={AXIS_TEXT}
          strokeOpacity={0.5}
          strokeDasharray="4 4"
          label={{ value: "Strong", position: "insideTopRight", fill: AXIS_TEXT, fontSize: 11 }}
        />
        <Tooltip
          cursor={{ stroke: CROSSHAIR, strokeDasharray: "3 3" }}
          content={({ active, payload }: TooltipProps<number, string>) => {
            if (!active || !payload?.length) return null;
            const p = payload[0].payload as History[number];
            return (
              <TooltipCard
                title={`Score ${p.score}`}
                lines={[p.title, `Attempt #${p.attempt} · ${shortDate(p.completed_at)}`]}
              />
            );
          }}
        />
        <Area
          type="monotone"
          dataKey="score"
          stroke={ACCENT}
          strokeWidth={2}
          fill="url(#scoreFill)"
          dot={false}
          activeDot={{ r: 5, fill: CROSSHAIR, stroke: SURFACE, strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

type Daily = ProgressSummary["daily"];

/** Exercises per day for the last two weeks — rounded columns on a recessive track. */
export function DailyActivityChart({ daily, height = 200 }: { daily: Daily; height?: number }) {
  if (daily.every((d) => d.sessions === 0)) {
    return <EmptyChart message="No practice in the last two weeks yet." />;
  }
  const data = daily.map((d) => ({
    ...d,
    day: new Date(`${d.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "narrow" }),
  }));
  const max = Math.max(...data.map((d) => d.sessions), 1);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 0, left: 0, bottom: 0 }} barCategoryGap="28%">
        <XAxis dataKey="day" tick={TICK} tickLine={false} axisLine={false} interval={0} />
        <YAxis hide domain={[0, max]} />
        <Tooltip
          cursor={false}
          content={({ active, payload }: TooltipProps<number, string>) => {
            if (!active || !payload?.length) return null;
            const p = payload[0].payload as Daily[number];
            return (
              <TooltipCard
                title={shortDate(`${p.date}T00:00:00`)}
                lines={[
                  `${p.sessions} exercise${p.sessions === 1 ? "" : "s"}`,
                  p.average_score !== null ? `Average score ${p.average_score}` : "No practice",
                ]}
              />
            );
          }}
        />
        <Bar
          dataKey="sessions"
          fill={ACCENT}
          radius={[6, 6, 6, 6]}
          background={{ fill: TRACK, radius: 6 }}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

type Weekly = ProgressSummary["weekly"];

/** Exercises per week, oldest to newest; minutes and average score in the tooltip. */
export function WeeklyColumns({ weekly, height = 220 }: { weekly: Weekly; height?: number }) {
  const data = [...weekly].reverse();
  if (data.every((w) => w.sessions === 0)) {
    return <EmptyChart message="No practice in the last four weeks." />;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 4, left: -20, bottom: 0 }} barCategoryGap="30%">
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="label" tick={TICK} tickLine={false} axisLine={false} interval={0} />
        <YAxis allowDecimals={false} tick={TICK} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          content={({ active, payload }: TooltipProps<number, string>) => {
            if (!active || !payload?.length) return null;
            const w = payload[0].payload as Weekly[number];
            return (
              <TooltipCard
                title={w.label}
                lines={[
                  `${w.sessions} exercise${w.sessions === 1 ? "" : "s"} · ${w.minutes} min`,
                  w.average_score !== null ? `Average score ${w.average_score}` : "No practice",
                ]}
              />
            );
          }}
        />
        <Bar dataKey="sessions" fill={ACCENT} radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Semicircle gauge for one 0–100 headline value. */
export function ScoreGauge({ value, label }: { value: number | null; label: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const r = 80;
  const cx = 100;
  const cy = 96;
  const angle = Math.PI * (1 - v / 100);
  const end = { x: cx + r * Math.cos(angle), y: cy - r * Math.sin(angle) };
  const track = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`;
  return (
    <figure className="mx-auto w-full max-w-[240px]">
      <svg viewBox="0 0 200 110" role="img" aria-label={`${label}: ${value ?? "no data"} out of 100`}>
        <path d={track} fill="none" stroke={TRACK} strokeWidth={22} strokeLinecap="round" />
        {value !== null && v > 0 && (
          <path d={arc} fill="none" stroke={ACCENT} strokeWidth={22} strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 6} textAnchor="middle" className="fill-ink font-display" fontSize="30" fontWeight="600">
          {value ?? "—"}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill={AXIS_TEXT} fontSize="11">
          out of 100
        </text>
      </svg>
    </figure>
  );
}

type ByType = ProgressSummary["by_type"];

/** Share of practice by exercise type — donut with a legend that carries the numbers. */
export function PracticeMixDonut({ byType }: { byType: ByType }) {
  if (byType.length === 0) return <EmptyChart message="No exercises yet." />;
  const total = byType.reduce((n, t) => n + t.sessions, 0);
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="h-[170px] w-[170px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              content={({ active, payload }: TooltipProps<number, string>) => {
                if (!active || !payload?.length) return null;
                const t = payload[0].payload as ByType[number];
                return (
                  <TooltipCard
                    title={t.label}
                    lines={[`${t.sessions} of ${total} exercises`, `Average score ${t.average_score ?? "—"}`]}
                  />
                );
              }}
            />
            <Pie
              data={byType}
              dataKey="sessions"
              nameKey="label"
              innerRadius={52}
              outerRadius={80}
              stroke={SURFACE}
              strokeWidth={2}
              startAngle={90}
              endAngle={-270}
              isAnimationActive={false}
            >
              {byType.map((t) => (
                <Cell key={t.type} fill={TYPE_COLORS[t.type]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full space-y-2 text-sm">
        {byType.map((t) => (
          <li key={t.type} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: TYPE_COLORS[t.type] }} />
            <span className="flex-1 text-ink">{t.label}</span>
            <span className="tabular-nums text-ink-soft">{Math.round((t.sessions / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

type FirstVsLatest = ProgressSummary["first_vs_latest"];

/** "Reading — Beginner: Sam and Max" → "Sam and Max" so the axis label fits. */
function shortTitle(title: string) {
  const tail = title.split(" — ").pop() ?? title;
  const name = tail.includes(": ") ? tail.split(": ").pop()! : tail;
  return name.length > 16 ? `${name.slice(0, 15)}…` : name;
}

/** First attempt against latest attempt per exercise — grouped horizontal bars with a legend. */
export function FirstVsLatestChart({ rows }: { rows: FirstVsLatest }) {
  if (rows.length === 0) {
    return <EmptyChart message="Repeat an exercise to compare your first try with your latest." />;
  }
  const data = rows.slice(0, 6);
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 56 + 50)}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }} barGap={2} barCategoryGap="26%">
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={TICK} tickLine={false} axisLine={false} />
        <YAxis
          type="category"
          dataKey="title"
          width={120}
          tick={{ ...TICK, fill: "#ECECF1" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={shortTitle}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          content={({ active, payload }: TooltipProps<number, string>) => {
            if (!active || !payload?.length) return null;
            const r = payload[0].payload as FirstVsLatest[number];
            return (
              <TooltipCard
                title={r.title}
                lines={[
                  `First try ${r.first_score} → latest ${r.latest_score}`,
                  `${r.change >= 0 ? "+" : ""}${r.change} points over ${r.attempts} tries`,
                ]}
              />
            );
          }}
        />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: AXIS_TEXT }} />
        <Bar dataKey="first_score" name="First try" fill={CATEGORICAL[2]} radius={[0, 4, 4, 0]} maxBarSize={14} isAnimationActive={false} />
        <Bar dataKey="latest_score" name="Latest" fill={CATEGORICAL[0]} radius={[0, 4, 4, 0]} maxBarSize={14} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
