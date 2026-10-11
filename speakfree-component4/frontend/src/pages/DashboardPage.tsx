import { useNavigate } from "react-router-dom";
import { HeartPulse, LogOut, Play, History, Target, Award } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useSession } from "../context/SessionContext";
import { usePracticeHistory } from "../context/PracticeHistoryContext";

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
  const { user, logout } = useAuth();
  const { resetSession } = useSession();
  const { progress } = usePracticeHistory();
  const recent = progress?.recent ?? [];

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleStartTherapy = () => {
    resetSession();
    navigate("/therapy");
  };

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-teal-100 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-600 text-white">
              <HeartPulse size={15} />
            </div>
            <span className="font-display font-semibold text-ink">SpeakFree Therapy</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-ink-soft">Hi, {user?.name ?? "there"}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm text-ink-soft hover:bg-teal-50"
            >
              <LogOut size={15} />
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-8 px-6 py-10">
        <div className="rounded-3xl bg-gradient-to-br from-teal-600 to-teal-700 p-8 text-white">
          <h1 className="font-display text-2xl font-semibold">
            Welcome back, {user?.name ?? "friend"}
          </h1>
          <p className="mt-1 text-teal-50">
            {progress?.has_data
              ? `${progress.trend.label}. Reading level: ${progress.level.label}.`
              : "Start with a Beginner reading — your plan will adapt as you practise."}
          </p>
          <button
            onClick={handleStartTherapy}
            className="mt-5 flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-teal-700 hover:bg-teal-50"
          >
            <Play size={16} />
            Open Therapy Assistant
          </button>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <History className="text-teal-600" size={20} />
            <p className="mt-3 font-display text-2xl font-semibold text-ink">
              {progress?.total_sessions ?? 0}
            </p>
            <p className="text-sm text-ink-soft">Exercises completed</p>
          </div>
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <Target className="text-teal-600" size={20} />
            <p className="mt-3 font-display text-2xl font-semibold text-ink">
              {progress?.level.label ?? "Beginner"}
            </p>
            <p className="text-sm text-ink-soft">Reading level</p>
          </div>
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <Award className="text-teal-600" size={20} />
            <p className="mt-3 font-display text-2xl font-semibold text-ink">
              {progress?.average_score ?? "—"}
            </p>
            <p className="text-sm text-ink-soft">Average score out of 100</p>
          </div>
        </div>

        <div className="rounded-2xl border border-teal-100 bg-white p-6">
          <h2 className="font-display font-semibold text-ink">Recent activity</h2>

          {recent.length === 0 ? (
            <p className="mt-2 text-sm text-ink-soft">
              No sessions yet — your practice history will appear here once you
              complete one.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {recent.map((entry) => (
                <li
                  key={entry.id}
                  className="flex items-center justify-between rounded-xl bg-paper px-4 py-3 text-sm"
                >
                  <span className="text-ink">{entry.title}</span>
                  <span className="text-xs text-ink-soft">
                    Score {entry.score} · {formatRelativeTime(entry.completed_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}