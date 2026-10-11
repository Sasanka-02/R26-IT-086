import { ReactNode } from "react";
import { Award, CalendarCheck, CheckCircle2, Circle, Clock, Flame, Lightbulb, Lock, Medal, Target, TrendingUp } from "lucide-react";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { Badge, FirstVsLatest, GoalProgress, LevelState, ProgressSummary } from "../types/therapy";

const LEVEL_STEPS = ["Beginner", "Intermediate", "Advanced (final stage)"];

const TREND_TONE: Record<string, string> = {
  Improving: "border-teal-200 bg-teal-50 text-teal-800",
  Steady: "border-teal-100 bg-paper text-ink",
  "Dipped a little": "border-amber-200 bg-amber-50 text-amber-900",
};

const RATING_LABEL = { easy: "Felt easy", ok: "Felt okay", hard: "Felt hard" };

function scoreTone(score: number | null) {
  if (score === null) return "text-ink-soft";
  if (score >= 65) return "text-teal-700";
  if (score >= 45) return "text-gold-600";
  return "text-amber-800";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds: number) {
  const total = Math.round(seconds);
  if (total < 60) return `${total} sec`;
  return `${Math.floor(total / 60)} min ${total % 60} sec`;
}

function LevelLadder({ level }: { level: LevelState }) {
  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-5">
      <div className="flex items-center gap-2">
        <Target size={18} className="text-teal-600" />
        <h3 className="text-base font-semibold text-ink">Reading level</h3>
      </div>
      <ol className="mt-4 grid gap-2 sm:grid-cols-3">
        {LEVEL_STEPS.map((label, i) => {
          const done = i < level.level_index || (level.mastered && i === level.level_index);
          const current = i === level.level_index && !level.mastered;
          return (
            <li
              key={label}
              className={`rounded-xl border px-4 py-3 text-sm ${
                current
                  ? "border-teal-600 bg-teal-600 text-white"
                  : done
                  ? "border-teal-200 bg-teal-50 text-teal-800"
                  : "border-dashed border-teal-100 bg-paper text-ink-soft"
              }`}
            >
              <span className="block text-xs opacity-80">Step {i + 1}</span>
              <span className="font-semibold">{label}</span>
              <span className="block text-xs opacity-80">
                {done ? "Completed" : current ? "You are here" : "Locked"}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-sm text-ink-soft">{level.progress_text}</p>
    </div>
  );
}

function Goals({ goals }: { goals: GoalProgress[] }) {
  if (goals.length === 0) return null;
  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-5">
      <h3 className="text-base font-semibold text-ink">Goals from your therapist</h3>
      <ul className="mt-3 space-y-2">
        {goals.map((g) => (
          <li key={g.id} className="flex items-start gap-2 rounded-xl bg-paper px-4 py-3 text-sm">
            {g.met ? (
              <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-teal-600" />
            ) : (
              <Circle size={18} className="mt-0.5 shrink-0 text-ink-soft" />
            )}
            <span>
              <span className="font-medium text-ink">{g.text}</span>
              <span className="block text-xs text-ink-soft">
                Now: {g.current ?? "no data yet"} · {g.met ? "Goal met" : "Not met yet"}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Badges({ badges }: { badges: Badge[] }) {
  const earned = badges.filter((b) => b.earned).length;
  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-5">
      <div className="flex items-center gap-2">
        <Medal size={18} className="text-gold-500" />
        <h3 className="text-base font-semibold text-ink">
          Badges · {earned} of {badges.length}
        </h3>
      </div>
      <ul className="mt-3 grid gap-2 sm:grid-cols-3">
        {badges.map((b) => (
          <li
            key={b.id}
            className={`rounded-xl border px-3 py-2 text-sm ${
              b.earned ? "border-gold-400/60 bg-gold-400/10" : "border-dashed border-teal-100 opacity-60"
            }`}
          >
            <span className="flex items-center gap-1.5 font-semibold text-ink">
              {b.earned ? <Medal size={14} className="text-gold-600" /> : <Lock size={13} />}
              {b.title}
            </span>
            <span className="text-xs text-ink-soft">{b.description}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FirstVsLatestTable({ rows }: { rows: FirstVsLatest[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-5">
      <h3 className="text-base font-semibold text-ink">First try vs latest</h3>
      <p className="mt-1 text-sm text-ink-soft">Your first attempt is your baseline — here is how far you've come.</p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm tabular-nums">
          <thead className="text-xs text-ink-soft">
            <tr className="border-b border-teal-100">
              <th className="py-2 pr-3 font-medium">Exercise</th>
              <th className="py-2 pr-3 text-right font-medium">Tries</th>
              <th className="py-2 pr-3 text-right font-medium">First</th>
              <th className="py-2 pr-3 text-right font-medium">Latest</th>
              <th className="py-2 text-right font-medium">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.exercise_id} className="border-b border-teal-50 last:border-0">
                <td className="py-2 pr-3 text-ink">{r.title}</td>
                <td className="py-2 pr-3 text-right text-ink-soft">{r.attempts}</td>
                <td className="py-2 pr-3 text-right text-ink">{r.first_score}</td>
                <td className="py-2 pr-3 text-right text-ink">{r.latest_score}</td>
                <td className={`py-2 text-right font-semibold ${r.change >= 0 ? "text-teal-700" : "text-amber-800"}`}>
                  {r.change > 0 ? "+" : ""}
                  {r.change}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: ReactNode;
  value: string;
  label: string;
}) {
  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-4">
      {icon}
      <p className="mt-2 font-display text-xl font-semibold text-ink">{value}</p>
      <p className="text-xs text-ink-soft">{label}</p>
    </div>
  );
}

function Dashboard({ data }: { data: ProgressSummary }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink">Your progress</h2>
        <p className="mt-1 text-sm text-ink-soft">
          Based only on the exercises you have completed with this account.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={<CalendarCheck className="text-teal-600" size={18} />}
          value={String(data.total_sessions)}
          label="Exercises completed"
        />
        <StatCard
          icon={<Clock className="text-teal-600" size={18} />}
          value={`${data.total_minutes} min`}
          label="Total practice time"
        />
        <StatCard
          icon={<Flame className="text-gold-500" size={18} />}
          value={`${data.streak_days} day${data.streak_days === 1 ? "" : "s"}`}
          label="Current streak"
        />
        <StatCard
          icon={<Award className="text-teal-600" size={18} />}
          value={data.average_score !== null ? `${data.average_score} / 100` : "—"}
          label={`Average score (best ${data.best_score ?? "—"})`}
        />
      </div>

      <div className={`rounded-2xl border p-5 ${TREND_TONE[data.trend.label] ?? TREND_TONE.Steady}`}>
        <div className="flex items-center gap-2">
          <TrendingUp size={18} />
          <h3 className="text-base font-semibold">Overall: {data.trend.label}</h3>
        </div>
        <p className="mt-1 text-sm">{data.trend.detail}</p>
      </div>

      <LevelLadder level={data.level} />

      <Goals goals={data.goals} />

      {data.highlights.length > 0 && (
        <div className="rounded-2xl border border-teal-100 bg-white p-5">
          <div className="flex items-center gap-2">
            <Lightbulb size={18} className="text-gold-500" />
            <h3 className="text-base font-semibold text-ink">What this means for you</h3>
          </div>
          <ul className="mt-3 list-disc space-y-1.5 pl-6 text-sm text-ink">
            {data.highlights.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      <FirstVsLatestTable rows={data.first_vs_latest} />

      <Badges badges={data.badges} />

      <div className="rounded-2xl border border-teal-100 bg-white p-5">
        <h3 className="text-base font-semibold text-ink">Week by week</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-soft">
              <tr className="border-b border-teal-100">
                <th className="py-2 pr-3 font-medium">Week</th>
                <th className="py-2 pr-3 font-medium">Exercises</th>
                <th className="py-2 pr-3 font-medium">Practice time</th>
                <th className="py-2 font-medium">Average score</th>
              </tr>
            </thead>
            <tbody>
              {data.weekly.map((week) => (
                <tr key={week.label} className="border-b border-teal-50 last:border-0">
                  <td className="py-2 pr-3 text-ink">{week.label}</td>
                  <td className="py-2 pr-3 text-ink">{week.sessions}</td>
                  <td className="py-2 pr-3 text-ink">{week.minutes} min</td>
                  <td className={`py-2 font-semibold ${scoreTone(week.average_score)}`}>
                    {week.average_score ?? "No practice"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-2xl border border-teal-100 bg-white p-5">
        <h3 className="text-base font-semibold text-ink">By exercise type</h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {data.by_type.map((t) => (
            <div key={t.type} className="rounded-xl bg-paper px-4 py-3 text-sm">
              <p className="font-semibold text-ink">{t.label}</p>
              <p className="mt-1 text-ink-soft">
                {t.sessions} time{t.sessions === 1 ? "" : "s"} · average{" "}
                <span className={`font-semibold ${scoreTone(t.average_score)}`}>
                  {t.average_score}
                </span>{" "}
                · best {t.best_score}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-teal-100 bg-white p-5">
        <h3 className="text-base font-semibold text-ink">Recent exercises</h3>
        <ul className="mt-3 space-y-2">
          {data.recent.map((r) => (
            <li
              key={r.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-paper px-4 py-3 text-sm"
            >
              <div>
                <p className="font-medium text-ink">{r.title}</p>
                <p className="text-xs text-ink-soft">
                  {formatDate(r.completed_at)} · {formatDuration(r.duration_seconds)} ·{" "}
                  {RATING_LABEL[r.self_rating]}
                </p>
              </div>
              <p className={`font-semibold ${scoreTone(r.score)}`}>
                {r.score} — {r.verdict}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ProgressDashboard() {
  const { progress, progressError, refresh } = usePracticeHistory();

  if (progressError) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4" role="alert">
        <p className="text-sm font-medium text-ink">We couldn't load your progress.</p>
        <p className="mt-1 text-sm text-ink-soft">
          Check that the therapy service is running, then try again.
        </p>
        <button
          onClick={refresh}
          className="mt-3 rounded-lg bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!progress) return <p className="text-sm text-ink-soft">Loading your progress...</p>;

  if (!progress.has_data) {
    return (
      <div className="space-y-5">
        <div className="rounded-2xl border border-teal-100 bg-white p-6">
          <h2 className="font-display text-xl font-semibold text-ink">No results yet</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Complete any exercise from the Practice tab and save your result. Your scores,
            streak and level will appear here, written out in plain language.
          </p>
        </div>
        <LevelLadder level={progress.level} />
        <Goals goals={progress.goals} />
        <Badges badges={progress.badges} />
      </div>
    );
  }

  return <Dashboard data={progress} />;
}
