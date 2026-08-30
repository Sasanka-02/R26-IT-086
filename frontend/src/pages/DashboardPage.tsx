import { useNavigate } from "react-router-dom";
import {
  Mic,
  LogOut,
  Play,
  History,
  ShieldCheck,
  HeartPulse,
  UserCircle,
  Pencil,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useSession } from "../context/SessionContext";
import { useIntake } from "../context/IntakeContext";
import { DISORDER_TYPE_LABELS } from "../types/intake";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { resetSession } = useSession();
  const { intake, hasIntake } = useIntake();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleStartScreening = () => {
    resetSession();
    navigate("/start");
  };

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-teal-100 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-600 text-white">
              <Mic size={15} />
            </div>
            <span className="font-display font-semibold text-ink">SpeakFree</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-ink-soft">
              Hi, {user?.name ?? "there"}
            </span>
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
            Ready for a new screening? It takes about 5 minutes.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={handleStartScreening}
              className="flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-teal-700 hover:bg-teal-50"
            >
              <Play size={16} />
              Start New Screening
            </button>
            <button
              onClick={() => navigate("/therapy")}
              className="flex items-center gap-2 rounded-full border border-white/40 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
            >
              <HeartPulse size={16} />
              Practice Therapy Exercises
            </button>
          </div>
        </div>

        {/* Patient Profile — from intake form */}
        <div className="rounded-2xl border border-teal-100 bg-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <UserCircle className="text-teal-600" size={20} />
              <h2 className="font-display font-semibold text-ink">Patient Profile</h2>
            </div>
            <button
              onClick={() => navigate("/start")}
              className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:underline"
            >
              <Pencil size={12} />
              {hasIntake ? "Update" : "Complete intake"}
            </button>
          </div>

          {hasIntake && intake ? (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-soft">Name</p>
                <p className="mt-0.5 text-sm font-medium text-ink">{intake.nickname}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-soft">Age category</p>
                <p className="mt-0.5 text-sm font-medium text-ink">
                  {intake.ageCategory === "kids" ? "Child / Junior (4–12)" : "Adult / Teen (13+)"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-soft">
                  Known disorder type
                </p>
                <p className="mt-0.5 text-sm font-medium text-ink">
                  {intake.disorderType ? DISORDER_TYPE_LABELS[intake.disorderType] : "Not specified"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-soft">Consents</p>
                <p className="mt-0.5 flex items-center gap-1 text-sm font-medium text-teal-700">
                  <ShieldCheck size={14} /> All confirmed
                </p>
              </div>
              {intake.previousTherapyNotes && (
                <div className="sm:col-span-2">
                  <p className="text-xs uppercase tracking-wide text-ink-soft">
                    Previous therapy notes
                  </p>
                  <p className="mt-0.5 text-sm text-ink-soft">{intake.previousTherapyNotes}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="mt-3 text-sm text-ink-soft">
              No intake form on file yet — you'll be asked to complete one before
              your next screening.
            </p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <History className="text-teal-600" size={20} />
            <p className="mt-3 font-display text-2xl font-semibold text-ink">0</p>
            <p className="text-sm text-ink-soft">Screenings completed</p>
          </div>
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <ShieldCheck className="text-teal-600" size={20} />
            <p className="mt-3 font-display text-2xl font-semibold text-ink">Private</p>
            <p className="text-sm text-ink-soft">Audio processed per-session only</p>
          </div>
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <Mic className="text-teal-600" size={20} />
            <p className="mt-3 font-display text-2xl font-semibold text-ink">3 tasks</p>
            <p className="text-sm text-ink-soft">Picture, video, conversation</p>
          </div>
        </div>

        <div className="rounded-2xl border border-teal-100 bg-white p-6">
          <h2 className="font-display font-semibold text-ink">Recent screenings</h2>
          <p className="mt-2 text-sm text-ink-soft">
            No screenings yet — your history will appear here once you complete one.
          </p>
        </div>
      </main>
    </div>
  );
}