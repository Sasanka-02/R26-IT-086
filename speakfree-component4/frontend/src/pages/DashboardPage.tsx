import { useNavigate } from "react-router-dom";
import { Award, CalendarCheck, Clock, Flame, Play, Target, TrendingUp } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { useAuth } from "../context/AuthContext";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import AppShell from "../components/AppShell";
import BadgeShowcase from "../components/BadgeShowcase";
import { Card, KpiTile, MeterBar, ScorePill } from "../components/ui";
import {
  DailyActivityChart,
  ScoreGauge,
  ScoreTrendChart,
  ACCENT,
} from "../components/progressCharts";

const LEVEL_STEPS = ["Beginner", "Intermediate", "Advanced"];

function formatRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMins = Math.round(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.round(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { resetSession } = useSession();
  const { progress, progressError, refresh } = usePracticeHistory();
  const recent = progress?.recent ?? [];
  const thisWeek = progress?.weekly[0];
  const lastWeek = progress?.weekly[1];

  const startTherapy = () => {
    resetSession();
    navigate("/therapy?tab=practice");
  };

  const weekDelta = thisWeek && lastWeek ? thisWeek.sessions - lastWeek.sessions : 0;

  return (
    <AppShell>
      <div className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">
              Welcome back, {user?.name?.split(" ")[0] ?? "friend"}
            </h1>
            <p className="mt-1 text-sm text-ink-soft">
              {progress?.has_data
                ? `${progress.trend.label} · Reading level ${progress.level.label}`
                : "Start with a Beginner reading — your plan adapts as you practise."}
            </p>
          </div>
          <button
            onClick={startTherapy}
            className="flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm text-white"
          >
            <Play size={16} />
            Start practice
          </button>
        </div>

        {progressError && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
            We couldn't load your progress. Check that the therapy service is running.{" "}
            <button onClick={refresh} className="font-semibold text-gold-400 underline">
              Try again
            </button>
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-3">
          <Card title="Practice summary" subtitle="All exercises on this account" className="lg:col-span-2">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <KpiTile
                icon={CalendarCheck}
                tone="gold"
                value={progress?.total_sessions ?? 0}
                label="Exercises done"
                caption={
                  thisWeek
                    ? `${thisWeek.sessions} this week${weekDelta ? ` (${weekDelta > 0 ? "+" : ""}${weekDelta})` : ""}`
                    : undefined
                }
              />
              <KpiTile
                icon={Clock}
                tone="mint"
                value={`${progress?.total_minutes ?? 0}m`}
                label="Practice time"
                caption={thisWeek ? `${thisWeek.minutes} min this week` : undefined}
              />
              <KpiTile
                icon={Flame}
                tone="pink"
                value={progress?.streak_days ?? 0}
                label="Day streak"
                caption={progress ? `${progress.active_days} active days` : undefined}
              />
              <KpiTile
                icon={Award}
                tone="blue"
                value={progress?.average_score ?? "—"}
                label="Average score"
                caption={progress?.best_score != null ? `Best ${progress.best_score}` : undefined}
              />
            </div>
          </Card>

          <Card title="Daily activity" subtitle="Exercises per day · last 14 days">
            <DailyActivityChart daily={progress?.daily ?? []} height={190} />
          </Card>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <Card
            title="Recent exercises"
            className="lg:col-span-2"
            action={
              <button
                onClick={() => navigate("/therapy?tab=progress")}
                className="text-xs font-medium text-teal-600 hover:underline"
              >
                View all progress
              </button>
            }
          >
            {recent.length === 0 ? (
              <p className="text-sm text-ink-soft">
                No exercises yet — your history will appear here once you complete one.
              </p>
            ) : (
              <div className="-mx-5 overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead className="text-xs text-ink-soft">
                    <tr className="border-b border-snow/5">
                      <th className="px-5 py-2 font-medium">#</th>
                      <th className="py-2 pr-4 font-medium">Exercise</th>
                      <th className="w-1/3 py-2 pr-4 font-medium">Score</th>
                      <th className="py-2 pr-5 text-right font-medium">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.slice(0, 5).map((entry, i) => (
                      <tr key={entry.id} className="border-b border-snow/5 last:border-0">
                        <td className="px-5 py-3 tabular-nums text-ink-soft">{String(i + 1).padStart(2, "0")}</td>
                        <td className="py-3 pr-4 text-ink">{entry.title}</td>
                        <td className="py-3 pr-4">
                          <div className="flex items-center gap-3">
                            <MeterBar value={entry.score} color={ACCENT} />
                            <ScorePill score={entry.score} />
                          </div>
                        </td>
                        <td className="py-3 pr-5 text-right text-xs text-ink-soft">
                          {formatRelativeTime(entry.completed_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title="Reading level" subtitle={progress?.level.progress_text}>
            <ol className="space-y-2">
              {LEVEL_STEPS.map((label, i) => {
                const index = progress?.level.level_index ?? 0;
                const mastered = progress?.level.mastered ?? false;
                const done = i < index || (mastered && i === index);
                const current = i === index && !mastered;
                return (
                  <li
                    key={label}
                    className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm ${
                      current ? "bg-teal-600 font-semibold text-white" : "bg-shell/60 text-ink"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <Target size={15} className={current ? "" : done ? "text-teal-600" : "text-ink-soft"} />
                      {label}
                    </span>
                    <span className={`text-xs ${current ? "" : "text-ink-soft"}`}>
                      {done ? "Completed" : current ? "You are here" : "Locked"}
                    </span>
                  </li>
                );
              })}
            </ol>
          </Card>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <Card title="Average score" subtitle="Across every exercise">
            <ScoreGauge value={progress?.average_score ?? null} label="Average score" />
            <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-sm text-ink-soft">
              <TrendingUp size={15} className="text-teal-600" />
              {progress?.trend.detail ?? "Loading..."}
            </p>
          </Card>

          <Card title="Score trend" subtitle="Your score on each attempt" className="lg:col-span-2">
            <ScoreTrendChart history={progress?.history ?? []} height={240} />
          </Card>
        </div>

        <Card title="Your badges" subtitle="Earned by practising — hover a badge to see how to unlock it">
          <BadgeShowcase badges={progress?.badges ?? []} compact />
        </Card>
      </div>
    </AppShell>
  );
}
