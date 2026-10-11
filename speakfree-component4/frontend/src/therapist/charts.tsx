import {
  Area,
  Legend,
  LineChart,
  Scatter,
  ScatterChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from "recharts";

// One series per chart, so one hue: the brand emerald. Identity comes from titles and axes.
const SERIES = "#1E5E53";
const SURFACE = "#FCF9F3";
const GRID = "#E6DFD2";
const AXIS_TEXT = "#5F6C66";
const TICK = { fill: AXIS_TEXT, fontSize: 12 };

function TooltipCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg border border-teal-100 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-semibold text-ink">{title}</p>
      {lines.map((line) => (
        <p key={line} className="mt-0.5 text-ink-soft">
          {line}
        </p>
      ))}
    </div>
  );
}

/** Vertical columns — counts over time (e.g. exercises per day or week). */
export function ColumnChart<T extends Record<string, unknown>>({
  data,
  xKey,
  yKey,
  unit,
  height = 220,
}: {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  unit: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 8, left: 0, bottom: 0 }} barCategoryGap="20%">
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey={xKey} tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd" minTickGap={12} />
        <YAxis allowDecimals={false} tick={TICK} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          cursor={{ fill: "rgba(30, 94, 83, 0.06)" }}
          content={({ active, payload }: TooltipProps<number, string>) =>
            active && payload?.length ? (
              <TooltipCard
                title={String(payload[0].payload[xKey])}
                lines={[`${payload[0].value} ${unit}`]}
              />
            ) : null
          }
        />
        <Bar dataKey={yKey} fill={SERIES} maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Horizontal bars with the value at the tip — small category counts. */
export function HorizontalBars<T extends Record<string, unknown>>({
  data,
  labelKey,
  valueKey,
  unit,
}: {
  data: T[];
  labelKey: keyof T & string;
  valueKey: keyof T & string;
  unit: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={data.length * 52 + 16}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 40, left: 8, bottom: 8 }}>
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis
          type="category"
          dataKey={labelKey}
          tick={TICK}
          tickLine={false}
          axisLine={false}
          width={150}
        />
        <Tooltip
          cursor={{ fill: "rgba(30, 94, 83, 0.06)" }}
          content={({ active, payload }: TooltipProps<number, string>) =>
            active && payload?.length ? (
              <TooltipCard
                title={String(payload[0].payload[labelKey])}
                lines={[`${payload[0].value} ${unit}`]}
              />
            ) : null
          }
        />
        <Bar dataKey={valueKey} fill={SERIES} maxBarSize={24} radius={[0, 4, 4, 0]} minPointSize={2} isAnimationActive={false}>
          <LabelList dataKey={valueKey} position="right" fill={AXIS_TEXT} fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

interface ScorePoint {
  attempt: number;
  date: string;
  score: number;
  title: string;
}

/** Score for every saved exercise, oldest to newest, with the "strong" threshold marked. */
export function ScoreLineChart({ data, strongScore = 75 }: { data: ScorePoint[]; strongScore?: number }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis
          dataKey="attempt"
          tick={TICK}
          tickLine={false}
          axisLine={{ stroke: GRID }}
          tickFormatter={(n) => `#${n}`}
          interval="preserveStartEnd"
          minTickGap={16}
        />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={TICK} tickLine={false} axisLine={false} width={40} />
        <ReferenceLine
          y={strongScore}
          stroke={AXIS_TEXT}
          strokeOpacity={0.5}
          label={{ value: "Strong", position: "insideTopRight", fill: AXIS_TEXT, fontSize: 11 }}
        />
        <Tooltip
          cursor={{ stroke: AXIS_TEXT, strokeOpacity: 0.3 }}
          content={({ active, payload }: TooltipProps<number, string>) => {
            if (!active || !payload?.length) return null;
            const p = payload[0].payload as ScorePoint;
            return (
              <TooltipCard
                title={`Exercise #${p.attempt}: score ${p.score}`}
                lines={[p.title, new Date(p.date).toLocaleString()]}
              />
            );
          }}
        />
        <Area type="monotone" dataKey="score" stroke="none" fill={SERIES} fillOpacity={0.1} isAnimationActive={false} />
        <Line
          type="monotone"
          dataKey="score"
          stroke={SERIES}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          dot={{ r: 4, fill: SERIES, stroke: SURFACE, strokeWidth: 2 }}
          activeDot={{ r: 6, fill: SERIES, stroke: SURFACE, strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// Validated categorical palette (dataviz validator: all checks pass on the card surface).
export const SERIES_COLORS = ["#118A6F", "#D2702A", "#5566C8"];

/** Several series over the same x axis, with a legend (identity never by colour alone). */
export function MultiLineChart({
  data,
  xKey,
  series,
  yDomain,
  xFormatter,
  unit,
}: {
  data: Record<string, number>[];
  xKey: string;
  series: { key: string; label: string }[];
  yDomain?: [number, number];
  xFormatter?: (v: number) => string;
  unit: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey={xKey} tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} tickFormatter={xFormatter} minTickGap={16} />
        <YAxis domain={yDomain ?? ["auto", "auto"]} tick={TICK} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          cursor={{ stroke: AXIS_TEXT, strokeOpacity: 0.3 }}
          content={({ active, payload, label }: TooltipProps<number, string>) =>
            active && payload?.length ? (
              <TooltipCard
                title={xFormatter ? xFormatter(Number(label)) : String(label)}
                lines={payload.map((p) => `${p.name}: ${p.value} ${unit}`)}
              />
            ) : null
          }
        />
        <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, color: AXIS_TEXT }} />
        {series.map((s, i) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stroke={SERIES_COLORS[i]}
            strokeWidth={2}
            strokeDasharray={i === 0 ? undefined : i === 1 ? "6 3" : "2 3"}
            dot={false}
            activeDot={{ r: 5, stroke: SURFACE, strokeWidth: 2 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Model score against the therapist's score for each rated attempt. Points on
 *  the diagonal mean perfect agreement. */
export function AgreementScatter({ data }: { data: { auto: number; expert: number; title: string }[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 16, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis type="number" dataKey="expert" name="Therapist" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]}
          tick={TICK} tickLine={false} axisLine={{ stroke: GRID }}
          label={{ value: "Therapist score (rating 1–5 → 0–100)", position: "insideBottom", offset: -4, fill: AXIS_TEXT, fontSize: 11 }} />
        <YAxis type="number" dataKey="auto" name="App" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]}
          tick={TICK} tickLine={false} axisLine={false} width={40} />
        <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 100, y: 100 }]} stroke={AXIS_TEXT} strokeOpacity={0.4} />
        <Tooltip
          content={({ active, payload }: TooltipProps<number, string>) => {
            if (!active || !payload?.length) return null;
            const p = payload[0].payload as { auto: number; expert: number; title: string };
            return <TooltipCard title={p.title} lines={[`App score ${p.auto}`, `Therapist ${p.expert}`]} />;
          }}
        />
        <Scatter data={data} fill={SERIES} stroke={SURFACE} strokeWidth={2} isAnimationActive={false} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
