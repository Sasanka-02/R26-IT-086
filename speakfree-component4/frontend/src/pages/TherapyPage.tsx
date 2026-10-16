import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowLeft, Lock, Search, Star, X } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { startTherapySession, endTherapySession, getUserExercises } from "../therapy/therapyApi";
import { LevelState, TherapyExercise, WordLevelState } from "../types/therapy";
import PacingExercise from "../therapy/PacingExercise";
import DafExercise from "../therapy/DafExercise";
import DafCalibration from "../therapy/DafCalibration";
import PictureDescriptionExercise from "../therapy/PictureDescriptionExercise";
import WordPracticeExercise from "../therapy/WordPracticeExercise";
import ProgressDashboard from "../therapy/ProgressDashboard";
import WeeklyPlan from "../therapy/WeeklyPlan";
import PrivacyPanel from "../therapy/PrivacyPanel";
import AssistantPanel from "../therapy/AssistantPanel";
import UsabilitySurvey from "../components/UsabilitySurvey";
import AppShell from "../components/AppShell";

const TABS = ["practice", "assistant", "progress", "plan", "privacy"] as const;
type Tab = (typeof TABS)[number];

const LEVEL_NAMES: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced · Final stage",
};

/** "Word Level 1–7", then "Phrase Stage 1–3"; the bonus set has no level. */
function wordBadge(wordLevel: number | null | undefined) {
  if (!wordLevel) return "Bonus";
  return wordLevel <= 7 ? `Word Level ${wordLevel}` : `Phrase Stage ${wordLevel - 7}`;
}

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
      {exercise.type === "words" && exercise.words && (
        <div
          className="flex h-24 items-center justify-center gap-3 border-b border-teal-100 bg-[#FFF4CC] text-4xl"
          aria-hidden="true"
        >
          {exercise.words.slice(0, 4).map((w) => (
            <span key={w.text}>{w.emoji}</span>
          ))}
        </div>
      )}
      <div className="p-5">
        <div className="flex flex-wrap gap-2">
          {exercise.type === "words" && (
            <span className="rounded-full bg-[#FFE6A7] px-2.5 py-0.5 text-xs font-semibold text-[#1f2937]">
              {wordBadge(exercise.word_level)}
            </span>
          )}
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
            ? exercise.type === "words"
              ? "Finish the word level before this one to unlock it."
              : "Complete the previous reading level to unlock this one."
            : exercise.description}
        </p>
      </div>
    </button>
  );
}

export default function TherapyPage() {
  const [params, setParams] = useSearchParams();
  const { sessionId } = useSession();
  const { userId, version } = usePracticeHistory();
  const tabParam = params.get("tab") as Tab | null;
  const tab: Tab = tabParam && TABS.includes(tabParam) ? tabParam : "practice";
  const query = (params.get("q") ?? "").trim().toLowerCase();
  const [exercises, setExercises] = useState<TherapyExercise[]>([]);
  const [level, setLevel] = useState<LevelState | null>(null);
  const [wordLevel, setWordLevel] = useState<WordLevelState | null>(null);
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
        setWordLevel(data.word_level);
        setLoadError(false);
      })
      .catch(() => active && setLoadError(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [userId, version]);

  const select = (exercise: TherapyExercise) => {
    if (exercise.locked) return;
    setSelected(exercise);
    setCalibratedDelay(null);
    setAttempt((n) => n + 1);
  };

  const startById = (exerciseId: string) => {
    const exercise = exercises.find((ex) => ex.id === exerciseId);
    if (!exercise) return;
    keepSelection.current = tab !== "practice" || !!query;
    setParams({ tab: "practice" });
    select(exercise);
  };

  const backToPicker = () => {
    setSelected(null);
    setCalibratedDelay(null);
  };

  // Picking a sidebar item while an exercise is open returns to the picker.
  // (Skipped once when the assistant or plan starts an exercise by switching to Practice.)
  const keepSelection = useRef(false);
  useEffect(() => {
    if (keepSelection.current) {
      keepSelection.current = false;
      return;
    }
    setSelected(null);
    setCalibratedDelay(null);
  }, [tab, query]);

  const visible = query
    ? exercises.filter((ex) => `${ex.title} ${ex.description}`.toLowerCase().includes(query))
    : exercises;
  const reading = visible.filter((ex) => ex.type === "reading");
  const pictures = visible.filter((ex) => ex.type === "picture");
  const words = visible.filter((ex) => ex.type === "words");
  const other = visible.filter((ex) => ex.type === "pacing" || ex.type === "daf");

  const section = (title: string, hint: string, items: TherapyExercise[]) =>
    items.length > 0 && (
      <section className="space-y-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
          <p className="text-sm text-ink-soft">{hint}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((ex) => (
            <ExerciseCard
              key={ex.id}
              exercise={ex}
              current={
                ex.type === "words"
                  ? !!wordLevel && ex.word_level === wordLevel.level
                  : !!level && ex.level === level.level
              }
              onSelect={() => select(ex)}
            />
          ))}
        </div>
      </section>
    );

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
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
                <UsabilitySurvey refreshKey={version} />
                <div>
                  <h1 className="font-display text-xl font-semibold text-ink">
                    Choose a practice exercise
                  </h1>
                  <p className="mt-1 text-sm text-ink-soft">
                    Word cards for children, graded reading, picture description, pacing and
                    delayed auditory feedback. After each exercise you'll get a score and your plan adapts.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {level && (
                      <p className="inline-flex rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800">
                        Reading level: {level.label} — {level.progress_text}
                      </p>
                    )}
                    {wordLevel && wordLevel.rounds > 0 && (
                      <p className="inline-flex rounded-full border border-gold-400/50 bg-gold-400/10 px-3 py-1 text-xs font-medium text-gold-600">
                        Words: {wordLevel.progress_text}
                      </p>
                    )}
                  </div>
                </div>
                {query && (
                  <div className="flex flex-wrap items-center gap-3 rounded-xl border border-teal-100 bg-white px-4 py-3 text-sm">
                    <Search size={15} className="text-ink-soft" />
                    <span className="text-ink">
                      {visible.length} exercise{visible.length === 1 ? "" : "s"} matching “{params.get("q")}”
                    </span>
                    <button
                      onClick={() => setParams({ tab: "practice" })}
                      className="ml-auto flex items-center gap-1 text-xs font-medium text-teal-600 hover:underline"
                    >
                      <X size={13} /> Clear search
                    </button>
                  </div>
                )}
                {section(
                  "Word practice (children)",
                  "Picture cards, one word at a time. One good round unlocks the next word level.",
                  words
                )}
                {section(
                  "Reading practice",
                  "Three levels. One strong reading unlocks the next level.",
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

            {selected && selected.type === "words" && (
              <WordPracticeExercise key={attempt} exercise={selected} />
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
        {tab === "progress" && <ProgressDashboard />}
        {tab === "plan" && <WeeklyPlan onStart={startById} />}
        {tab === "privacy" && <PrivacyPanel />}
      </div>
    </AppShell>
  );
}
