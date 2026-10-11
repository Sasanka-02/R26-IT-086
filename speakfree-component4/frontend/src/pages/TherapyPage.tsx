import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { HeartPulse, ArrowLeft, Lock, Star } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { startTherapySession, endTherapySession, getUserExercises } from "../therapy/therapyApi";
import { LevelState, TherapyExercise } from "../types/therapy";
import PacingExercise from "../therapy/PacingExercise";
import DafExercise from "../therapy/DafExercise";
import DafCalibration from "../therapy/DafCalibration";
import PictureDescriptionExercise from "../therapy/PictureDescriptionExercise";
import ProgressDashboard from "../therapy/ProgressDashboard";
import WeeklyPlan from "../therapy/WeeklyPlan";
import PrivacyPanel from "../therapy/PrivacyPanel";
import AssistantPanel from "../therapy/AssistantPanel";

type Tab = "practice" | "assistant" | "dashboard" | "plan" | "privacy";

const LEVEL_NAMES: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced · Final stage",
};

function ExerciseCard({
  exercise,
  current,
  onSelect,
}: {
  exercise: TherapyExercise;
  current: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      disabled={exercise.locked}
      className={`flex flex-col overflow-hidden rounded-2xl border bg-white text-left transition ${
        exercise.locked
          ? "cursor-not-allowed border-dashed border-teal-100 opacity-60"
          : current
          ? "border-teal-600 shadow-sm hover:shadow"
          : "border-teal-100 hover:border-teal-400 hover:shadow-sm"
      }`}
    >
      {exercise.image_url && (
        <img
          src={exercise.image_url}
          alt=""
          className="h-32 w-full border-b border-teal-100 bg-paper object-cover"
        />
      )}
      <div className="p-5">
        <div className="flex flex-wrap gap-2">
          {exercise.level && (
            <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700">
              {LEVEL_NAMES[exercise.level]}
            </span>
          )}
          {current && (
            <span className="flex items-center gap-1 rounded-full bg-gold-400/20 px-2.5 py-0.5 text-xs font-medium text-gold-600">
              <Star size={11} /> Your level
            </span>
          )}
          {exercise.assigned && (
            <span className="rounded-full bg-gold-400/20 px-2.5 py-0.5 text-xs font-medium text-gold-600">
              Assigned by therapist
            </span>
          )}
          {exercise.locked && (
            <span className="flex items-center gap-1 rounded-full bg-paper px-2.5 py-0.5 text-xs font-medium text-ink-soft">
              <Lock size={11} /> Locked
            </span>
          )}
        </div>
        <h3 className="mt-2 font-display font-semibold text-ink">{exercise.title}</h3>
        <p className="mt-1 text-sm text-ink-soft">
          {exercise.locked
            ? "Complete the previous reading level to unlock this one."
            : exercise.description}
        </p>
      </div>
    </button>
  );
}

export default function TherapyPage() {
  const navigate = useNavigate();
  const { sessionId } = useSession();
  const { userId, version } = usePracticeHistory();
  const [tab, setTab] = useState<Tab>("practice");
  const [exercises, setExercises] = useState<TherapyExercise[]>([]);
  const [level, setLevel] = useState<LevelState | null>(null);
  const [selected, setSelected] = useState<TherapyExercise | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [calibratedDelay, setCalibratedDelay] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    startTherapySession(sessionId, "unknown").catch(() => {});
    return () => {
      endTherapySession(sessionId).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let active = true;
    getUserExercises(userId)
      .then((data) => {
        if (!active) return;
        setExercises(data.exercises);
        setLevel(data.level);
        setLoadError(false);
      })
      .catch(() => active && setLoadError(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [userId, version]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "practice", label: "Practice" },
    { id: "assistant", label: "Assistant" },
    { id: "dashboard", label: "My Progress" },
    { id: "plan", label: "Weekly Plan" },
    { id: "privacy", label: "Privacy" },
  ];

  const select = (exercise: TherapyExercise) => {
    if (exercise.locked) return;
    setSelected(exercise);
    setCalibratedDelay(null);
    setAttempt((n) => n + 1);
  };

  const startById = (exerciseId: string) => {
    const exercise = exercises.find((ex) => ex.id === exerciseId);
    if (!exercise) return;
    setTab("practice");
    select(exercise);
  };

  const backToPicker = () => {
    setSelected(null);
    setCalibratedDelay(null);
  };

  const reading = exercises.filter((ex) => ex.type === "reading");
  const pictures = exercises.filter((ex) => ex.type === "picture");
  const other = exercises.filter((ex) => ex.type === "pacing" || ex.type === "daf");

  const section = (title: string, hint: string, items: TherapyExercise[]) =>
    items.length > 0 && (
      <section className="space-y-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
          <p className="text-sm text-ink-soft">{hint}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {items.map((ex) => (
            <ExerciseCard
              key={ex.id}
              exercise={ex}
              current={!!level && ex.level === level.level}
              onSelect={() => select(ex)}
            />
          ))}
        </div>
      </section>
    );

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-teal-100 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
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

      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <div className="flex gap-1 overflow-x-auto rounded-full border border-teal-100 bg-white p-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 whitespace-nowrap rounded-full px-3 py-2 text-sm font-medium transition ${
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
          <div className="space-y-6">
            {loading && <p className="text-sm text-ink-soft">Loading today's exercises...</p>}
            {loadError && (
              <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink">
                We couldn't load your exercises. Check that the therapy service is running.
              </p>
            )}

            {!loading && !selected && (
              <>
                <div>
                  <h1 className="font-display text-xl font-semibold text-ink">
                    Choose a practice exercise
                  </h1>
                  <p className="mt-1 text-sm text-ink-soft">
                    Graded reading, picture description, pacing and delayed auditory
                    feedback. After each exercise you'll get a score and your plan adapts.
                  </p>
                  {level && (
                    <p className="mt-3 inline-flex rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800">
                      Reading level: {level.label} — {level.progress_text}
                    </p>
                  )}
                </div>
                {section(
                  "Reading practice",
                  "Three levels. Two strong readings in a row unlock the next level.",
                  reading
                )}
                {section(
                  "Picture description",
                  "Describe each picture in your own words.",
                  pictures
                )}
                {section("Pacing & DAF", "Techniques for a smooth, steady rhythm.", other)}
              </>
            )}

            {selected && (selected.type === "pacing" || selected.type === "reading") && (
              <PacingExercise key={attempt} sessionId={sessionId} exercise={selected} />
            )}

            {selected && selected.type === "picture" && (
              <PictureDescriptionExercise key={attempt} exercise={selected} />
            )}

            {selected && selected.type === "daf" && !calibratedDelay && (
              <DafCalibration
                key={attempt}
                sessionId={sessionId}
                onCalibrated={(delay) => setCalibratedDelay(delay)}
              />
            )}

            {selected && selected.type === "daf" && calibratedDelay && (
              <DafExercise key={attempt} exercise={selected} initialDelayMs={calibratedDelay} />
            )}

            {selected && (
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={backToPicker}
                  className="flex items-center gap-1 text-sm font-medium text-teal-600 hover:underline"
                >
                  <ArrowLeft size={14} />
                  Choose a different exercise
                </button>
                <button
                  onClick={() => select(selected)}
                  className="text-sm font-medium text-teal-600 hover:underline"
                >
                  Try this one again
                </button>
              </div>
            )}
          </div>
        )}

        {tab === "assistant" && <AssistantPanel onStart={startById} />}
        {tab === "dashboard" && <ProgressDashboard />}
        {tab === "plan" && <WeeklyPlan onStart={startById} />}
        {tab === "privacy" && <PrivacyPanel />}
      </div>
    </div>
  );
}
