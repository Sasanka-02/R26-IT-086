import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { HeartPulse, ArrowLeft } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { startTherapySession, endTherapySession } from "../therapy/therapyApi";
import { TherapyExercise } from "../types/therapy";
import PacingExercise from "../therapy/PacingExercise";
import DafExercise from "../therapy/DafExercise";
import DafCalibration from "../therapy/DafCalibration";
import PictureDescriptionExercise from "../therapy/PictureDescriptionExercise";
import ProgressDashboard from "../therapy/ProgressDashboard";
import WeeklyPlan from "../therapy/WeeklyPlan";
import PrivacyPanel from "../therapy/PrivacyPanel";

type Tab = "practice" | "dashboard" | "plan" | "privacy";

export default function TherapyPage() {
  const navigate = useNavigate();
  const { sessionId } = useSession();
  const [tab, setTab] = useState<Tab>("practice");
  const [exercises, setExercises] = useState<TherapyExercise[]>([]);
  const [selected, setSelected] = useState<TherapyExercise | null>(null);
  const [calibratedDelay, setCalibratedDelay] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    startTherapySession(sessionId, "unknown")
      .then(setExercises)
      .finally(() => setLoading(false));

    return () => {
      endTherapySession(sessionId).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tabs: { id: Tab; label: string }[] = [
    { id: "practice", label: "Practice" },
    { id: "dashboard", label: "Dashboard" },
    { id: "plan", label: "Weekly Plan" },
    { id: "privacy", label: "Privacy" },
  ];

  const backToPicker = () => {
    setSelected(null);
    setCalibratedDelay(null);
  };

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-teal-100 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink"
          >
            <ArrowLeft size={15} />
            Dashboard
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-600 text-white">
              <HeartPulse size={14} />
            </div>
            <span className="font-display font-semibold text-ink">Therapy Assistant</span>
          </div>
          <div className="w-20" />
        </div>
      </header>

      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <div className="flex gap-1 rounded-full border border-teal-100 bg-white p-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 rounded-full px-3 py-2 text-sm font-medium transition ${
                tab === t.id
                  ? "bg-teal-600 text-white shadow-sm"
                  : "text-ink-soft hover:bg-teal-50"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "practice" && (
          <div className="space-y-5">
            {loading && <p className="text-sm text-ink-soft">Loading today's exercises...</p>}

            {!loading && !selected && (
              <>
                <div>
                  <h1 className="font-display text-xl font-semibold text-ink">
                    Choose a practice exercise
                  </h1>
                  <p className="mt-1 text-sm text-ink-soft">
                    Real-time pacing coaching, delayed auditory feedback, and
                    guided picture description — pick whichever fits today.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {exercises.map((ex) => (
                    <button
                      key={ex.id}
                      onClick={() => setSelected(ex)}
                      className="rounded-2xl border border-teal-100 bg-white p-5 text-left transition hover:border-teal-400 hover:shadow-sm"
                    >
                      <h3 className="font-display font-semibold text-ink">{ex.title}</h3>
                      <p className="mt-1 text-sm text-ink-soft">{ex.description}</p>
                    </button>
                  ))}
                </div>
              </>
            )}

            {selected && selected.type === "pacing" && (
              <PacingExercise sessionId={sessionId} exercise={selected} />
            )}

            {selected && selected.type === "picture" && (
              <PictureDescriptionExercise exercise={selected} />
            )}

            {selected && selected.type === "daf" && !calibratedDelay && (
              <DafCalibration
                sessionId={sessionId}
                onCalibrated={(delay) => setCalibratedDelay(delay)}
              />
            )}

            {selected && selected.type === "daf" && calibratedDelay && (
              <DafExercise exercise={selected} initialDelayMs={calibratedDelay} />
            )}

            {selected && (
              <button
                onClick={backToPicker}
                className="flex items-center gap-1 text-sm font-medium text-teal-600 hover:underline"
              >
                <ArrowLeft size={14} />
                Choose a different exercise
              </button>
            )}
          </div>
        )}

        {tab === "dashboard" && <ProgressDashboard sessionId={sessionId} />}
        {tab === "plan" && <WeeklyPlan sessionId={sessionId} />}
        {tab === "privacy" && <PrivacyPanel sessionId={sessionId} />}
      </div>
    </div>
  );
}