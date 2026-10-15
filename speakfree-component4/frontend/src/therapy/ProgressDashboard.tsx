import { useState } from "react";
import {
  Award,
  CalendarCheck,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock,
  Download,
  Flame,
  Lightbulb,
} from "lucide-react";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { GoalProgress, LevelState, ProgressSummary } from "../types/therapy";
import BadgeShowcase from "../components/BadgeShowcase";
import { LevelTimeline, ReportCard } from "../components/ReportCard";
import { Card, KpiTile, MeterBar, ScorePill } from "../components/ui";
import {
  ACCENT,
  DailyActivityChart,
  FirstVsLatestChart,
  PracticeMixDonut,
  ScoreGauge,
  ScoreTrendChart,
  TYPE_COLORS,
  WeeklyColumns,
} from "../components/progressCharts";

const LEVEL_STEPS = ["Beginner", "Intermediate", "Advanced (final stage)"];

const RATING_LABEL = { easy: "Felt easy", ok: "Felt okay", hard: "Felt hard" };

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
    <Card title="Reading level" subtitle={level.progress_text}>
      <ol className="relative space-y-3">
        {LEVEL_STEPS.map((label, i) => {
          const done = i < level.level_index || (level.mastered && i === level.level_index);
          const current = i === level.level_index && !level.mastered;
          return (
            <li key={label} className="flex items-center gap-3">
              <span
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                  current
                    ? "bg-teal-600 text-white"
                    : done
                    ? "bg-teal-600/15 text-teal-600"
                    : "border border-dashed border-snow/15 text-ink-soft"
                }`}
              >
                {done ? <CheckCircle2 size={17} /> : i + 1}
              </span>
              <div>
                <p className={`text-sm font-medium ${current || done ? "text-ink" : "text-ink-soft"}`}>{label}</p>
                <p className="text-xs text-ink-soft">
                  {done ? "Completed" : current ? "You are here" : "Locked"}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
      <div className="mt-5 border-t border-snow/5 pt-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-ink-soft">Level timeline</p>
        <LevelTimeline history={level.history} />
      </div>
    </Card>
  );
}

function Goals({ goals }: { goals: GoalProgress[] }) {
  if (goals.length === 0) return null;
  return (
    <Card title="Goals from your therapist">
      <ul className="space-y-2">
        {goals.map((g) => (
          <li key={g.id} className="flex items-start gap-2.5 rounded-xl bg-shell/60 px-4 py-3 text-sm">
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
    </Card>
  );
}

function Dashboard({ data }: { data: ProgressSummary }) {
  const [showDetails, setShowDetails] = useState(false);
  const thisWeek = data.weekly[0];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">My progress</h1>
          <p className="mt-1 text-sm text-ink-soft">
            Based only on the exercises you have completed with this account.
            <span className="hidden print:inline"> Report printed {new Date().toLocaleDateString()}.</span>
          </p>
        </div>
        <button
          onClick={() => window.print()}
          className="no-print inline-flex items-center gap-1.5 rounded-full border border-teal-600/40 px-4 py-1.5 text-sm font-medium text-teal-600 hover:bg-teal-600/10"
        >
          <Download size={14} />
          Download report (PDF)
        </button>
      </div>

      <ReportCard card={data.report_card} />

      <div className="grid gap-5 lg:grid-cols-2">
        <LevelLadder level={data.level} />
        <div className="space-y-5">
          {data.highlights.length > 0 && (
            <Card title="What this means for you">
              <ul className="space-y-2.5">
                {data.highlights.map((line) => (
                  <li key={line} className="flex gap-2.5 text-sm text-ink">
                    <Lightbulb size={16} className="mt-0.5 shrink-0 text-gold-400" />
                    {line}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          <Goals goals={data.goals} />
        </div>
      </div>

      <button
        onClick={() => setShowDetails((v) => !v)}
        aria-expanded={showDetails}
        className="no-print flex w-full items-center justify-between rounded-2xl border border-snow/5 bg-white px-5 py-4 text-left text-sm font-semibold text-ink hover:bg-shell/40"
      >
        <span>
          Details: charts and numbers
          <span className="block text-xs font-normal text-ink-soft">
            Score trend, weekly practice, practice mix, first try vs latest, badges and recent exercises
          </span>
        </span>
        <ChevronDown size={18} className={`shrink-0 transition ${showDetails ? "rotate-180" : ""}`} />
      </button>

      {showDetails && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiTile
              icon={CalendarCheck}
              tone="gold"
              value={data.total_sessions}
              label="Exercises completed"
              caption={thisWeek ? `${thisWeek.sessions} this week` : undefined}
            />
            <KpiTile
              icon={Clock}
              tone="mint"
              value={`${data.total_minutes} min`}
              label="Total practice time"
              caption={thisWeek ? `${thisWeek.minutes} min this week` : undefined}
            />
            <KpiTile
              icon={Flame}
              tone="pink"
              value={`${data.streak_days} day${data.streak_days === 1 ? "" : "s"}`}
              label="Current streak"
              caption={`${data.active_days} active days in total`}
            />
            <KpiTile
              icon={Award}
              tone="blue"
              value={data.average_score !== null ? `${data.average_score}` : "—"}
              label="Average score"
              caption={`Best ${data.best_score ?? "—"} out of 100`}
            />
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <Card title="Score trend" subtitle="Your score on each attempt (0–100)" className="lg:col-span-2">
              <ScoreTrendChart history={data.history} />
            </Card>
            <Card title="Average score" subtitle="Across every exercise">
              <ScoreGauge value={data.average_score} label="Average score" />
              <p className="mt-4 text-center text-sm text-ink-soft">{data.trend.detail}</p>
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <Card title="Weekly practice" subtitle="Exercises per week · hover for minutes and score">
              <WeeklyColumns weekly={data.weekly} />
            </Card>
            <Card title="Daily activity" subtitle="Exercises per day · last 14 days">
              <DailyActivityChart daily={data.daily} height={220} />
            </Card>
            <Card title="Practice mix" subtitle="Share of exercises by type">
              <PracticeMixDonut byType={data.by_type} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <Card
              title="First try vs latest"
              subtitle="Your first attempt is your baseline — here is how far you've come"
              className="lg:col-span-3"
            >
              <FirstVsLatestChart rows={data.first_vs_latest} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Score by exercise type" subtitle="Average score, with your best in brackets">
              <ul className="space-y-4">
                {data.by_type.map((t) => (
                  <li key={t.type}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-ink">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: TYPE_COLORS[t.type] }} />
                        {t.label}
                      </span>
                      <span className="tabular-nums text-ink-soft">
                        <span className="font-semibold text-ink">{t.average_score ?? "—"}</span> ({t.best_score}) ·{" "}
                        {t.sessions}×
                      </span>
                    </div>
                    <MeterBar value={t.average_score ?? 0} color={TYPE_COLORS[t.type]} />
                  </li>
                ))}
              </ul>
            </Card>

            <Card title="Badges" subtitle="Milestones you've reached">
              <BadgeShowcase badges={data.badges} />
            </Card>
          </div>

          <Card title="Recent exercises">
            <ul className="divide-y divide-snow/5">
              {data.recent.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-3 py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink">{r.title}</p>
                    <p className="text-xs text-ink-soft">
                      {formatDate(r.completed_at)} · {formatDuration(r.duration_seconds)} · {RATING_LABEL[r.self_rating]}
                    </p>
                  </div>
                  <div className="hidden w-40 sm:block">
                    <MeterBar value={r.score} color={ACCENT} />
                  </div>
                  <span className="w-28 text-right text-xs text-ink-soft">{r.verdict}</span>
                  <ScorePill score={r.score} />
                </li>
              ))}
            </ul>
          </Card>

          <details className="rounded-2xl border border-snow/5 bg-white p-5">
            <summary className="cursor-pointer text-sm font-semibold text-ink">Week by week (table view)</summary>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm tabular-nums">
                <thead className="text-xs text-ink-soft">
                  <tr className="border-b border-snow/5">
                    <th className="py-2 pr-3 font-medium">Week</th>
                    <th className="py-2 pr-3 font-medium">Exercises</th>
                    <th className="py-2 pr-3 font-medium">Practice time</th>
                    <th className="py-2 font-medium">Average score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.weekly.map((week) => (
                    <tr key={week.label} className="border-b border-snow/5 last:border-0">
                      <td className="py-2 pr-3 text-ink">{week.label}</td>
                      <td className="py-2 pr-3 text-ink">{week.sessions}</td>
                      <td className="py-2 pr-3 text-ink">{week.minutes} min</td>
                      <td className="py-2 text-ink">{week.average_score ?? "No practice"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </div>
  );
}

export default function ProgressDashboard() {
  const { progress, progressError, refresh } = usePracticeHistory();

  if (progressError) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4" role="alert">
        <p className="text-sm font-medium text-ink">We couldn't load your progress.</p>
        <p className="mt-1 text-sm text-ink-soft">Check that the therapy service is running, then try again.</p>
        <button onClick={refresh} className="mt-3 rounded-lg bg-teal-600 px-3 py-2 text-sm text-white">
          Try again
        </button>
      </div>
    );
  }

  if (!progress) return <p className="text-sm text-ink-soft">Loading your progress...</p>;

  if (!progress.has_data) {
    return (
      <div className="space-y-5">
        <ReportCard card={progress.report_card} />
        <Card title="No results yet">
          <p className="text-sm text-ink-soft">
            Complete any exercise from the Practice page and save your result. Your score trend, weekly
            activity, practice mix and badges will appear here as charts.
          </p>
        </Card>
        <div className="grid gap-5 lg:grid-cols-2">
          <LevelLadder level={progress.level} />
          <Goals goals={progress.goals} />
        </div>
        <Card title="Badges" subtitle="Milestones to work towards">
          <BadgeShowcase badges={progress.badges} />
        </Card>
      </div>
    );
  }

  return <Dashboard data={progress} />;
}
