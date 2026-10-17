import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ClipboardCheck, Headphones, RotateCcw } from "lucide-react";
import AppShell from "../components/AppShell";
import { PracticeHistoryProvider } from "../context/PracticeHistoryContext";
import { useAuth } from "../context/AuthContext";
import { useSession } from "../context/SessionContext";
import { ExerciseResultResponse, TherapyExercise } from "../types/therapy";
import { StudentRow } from "../types/therapist";
import { getUserExercises } from "../therapy/therapyApi";
import PacingExercise from "../therapy/PacingExercise";
import PictureDescriptionExercise from "../therapy/PictureDescriptionExercise";
import WordPracticeExercise from "../therapy/WordPracticeExercise";
import DafExercise from "../therapy/DafExercise";
import { getStudents, rateAttempt } from "./therapistApi";
import { Panel } from "./ui";

const SCALE = [
  { value: 1, label: "Very poor", hint: "Frequent blocks or repetitions; hard to follow" },
  { value: 2, label: "Poor", hint: "Many disfluencies; effortful" },
  { value: 3, label: "Fair", hint: "Some disfluencies; understandable" },
  { value: 4, label: "Good", hint: "Occasional disfluency; mostly smooth" },
  { value: 5, label: "Very fluent", hint: "Smooth, controlled, natural" },
];

const TYPE_ORDER = ["reading", "pacing", "picture", "words", "daf"];

function RatingRow({ who, value, onChange }: { who: string; value: number | null; onChange: (v: number) => void }) {
  return (
    <div>
      <p className="mb-1.5 text-sm font-medium text-ink">{who}</p>
      <div className="grid grid-cols-5 gap-2" role="radiogroup" aria-label={`${who} rating`}>
        {SCALE.map((s) => (
          <button
            key={s.value}
            role="radio"
            aria-checked={value === s.value}
            title={s.hint}
            onClick={() => onChange(s.value)}
            className={`rounded-xl border px-2 py-2 text-center text-sm transition ${
              value === s.value
                ? "border-teal-600 bg-teal-600 text-white"
                : "border-teal-100 text-ink hover:border-teal-400"
            }`}
          >
            <span className="block text-lg font-semibold">{s.value}</span>
            <span className="block text-[11px] leading-tight opacity-80">{s.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Expert validation session: a volunteer does an exercise on this device, the
 * speech-language pathologist listens to the recording here and rates it 1–5
 * before seeing the app's score. Recordings are saved with the attempt; the
 * measurements, the score and the rating are saved.
 */
export default function ValidationSessionPage() {
  const { user } = useAuth();
  const { sessionId } = useSession();
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [volunteer, setVolunteer] = useState("");
  const [secondRater, setSecondRater] = useState("");
  const [exercises, setExercises] = useState<TherapyExercise[]>([]);
  const [exercise, setExercise] = useState<TherapyExercise | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [saved, setSaved] = useState<ExerciseResultResponse | null>(null);
  const [rating1, setRating1] = useState<number | null>(null);
  const [rating2, setRating2] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tally, setTally] = useState(0);

  useEffect(() => {
    getStudents().then(setStudents).catch(() => setStudents([]));
  }, []);

  useEffect(() => {
    setExercise(null);
    if (!volunteer) return setExercises([]);
    getUserExercises(volunteer)
      .then((d) => setExercises(d.exercises))
      .catch(() => setExercises([]));
  }, [volunteer]);

  const nextAttempt = (same = true) => {
    setSaved(null);
    setRating1(null);
    setRating2(null);
    setNote("");
    setSubmitted(false);
    setError(null);
    if (!same) setExercise(null);
    setAttempt((n) => n + 1);
  };

  const submit = async () => {
    if (!saved || rating1 === null || (secondRater.trim() && rating2 === null)) return;
    setError(null);
    try {
      await rateAttempt(volunteer, saved.record.id, rating1, { heardAudio: true, note });
      if (secondRater.trim() && rating2 !== null) {
        await rateAttempt(volunteer, saved.record.id, rating2, { heardAudio: true, rater: secondRater.trim() });
      }
      setSubmitted(true);
      setTally((n) => n + 1);
    } catch {
      setError("The rating didn't save. Check the connection and try again.");
    }
  };

  const ordered = [...exercises].sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type));
  const name = students.find((s) => s.email === volunteer)?.name ?? volunteer;

  return (
    <AppShell>
      <main className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-600">Expert validation</p>
            <h1 className="mt-1 font-display text-3xl font-semibold text-ink">Validation session</h1>
            <p className="mt-1 max-w-3xl text-sm text-ink-soft">
              A volunteer does an exercise on this device. You listen to the recording here and rate it 1–5 —
              the app's score stays hidden until you have rated, so your judgement is independent. Recordings
              are saved with each attempt, so you can listen again later on the student's page.
            </p>
          </div>
          <div className="rounded-2xl border border-teal-100 bg-white px-5 py-3 text-center">
            <p className="font-display text-2xl font-semibold text-ink">{tally}</p>
            <p className="text-xs text-ink-soft">rated this session</p>
            <Link to="/therapist/evidence" className="text-xs font-medium text-teal-600 hover:underline">
              See results →
            </Link>
          </div>
        </div>

        <Panel title="1 · Who is practising, and who is rating?">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm text-ink-soft">
              Volunteer (student account)
              <select
                value={volunteer}
                onChange={(e) => {
                  setVolunteer(e.target.value);
                  nextAttempt(false);
                }}
                className="mt-1 block w-full rounded-xl border border-teal-100 bg-white px-3 py-2 text-sm text-ink"
              >
                <option value="">Choose a volunteer…</option>
                {students.map((s) => (
                  <option key={s.email} value={s.email}>
                    {s.name} · {s.email}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs">
                New volunteers sign up on the Create account page first (with consent).
              </span>
            </label>
            <div className="space-y-2 text-sm text-ink-soft">
              <p>
                Rater 1: <strong className="text-ink">{user?.name}</strong> (this login)
              </p>
              <label className="block">
                Rater 2 name (optional — for inter-rater agreement)
                <input
                  value={secondRater}
                  onChange={(e) => setSecondRater(e.target.value)}
                  placeholder="e.g. Ms. Perera, SLP"
                  maxLength={80}
                  className="mt-1 block w-full rounded-xl border border-teal-100 bg-white px-3 py-2 text-sm text-ink"
                />
              </label>
            </div>
          </div>
        </Panel>

        {volunteer && !exercise && (
          <Panel title="2 · Choose an exercise" subtitle="Rate a mix: every reading level, pacing, picture description, word practice and DAF.">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {ordered.map((ex) => (
                <button
                  key={ex.id}
                  onClick={() => {
                    setExercise(ex);
                    nextAttempt();
                  }}
                  className="rounded-xl border border-teal-100 bg-white px-4 py-3 text-left text-sm hover:border-teal-400"
                >
                  <span className="block text-xs uppercase tracking-wide text-ink-soft">{ex.type}</span>
                  <span className="font-medium text-ink">{ex.title}</span>
                </button>
              ))}
            </div>
          </Panel>
        )}

        {volunteer && exercise && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-ink-soft">
                3 · <strong className="text-ink">{name}</strong> does the exercise, then picks how it felt and saves.
              </p>
              <button onClick={() => nextAttempt(false)} className="text-sm font-medium text-teal-600 hover:underline">
                Choose a different exercise
              </button>
            </div>

            <PracticeHistoryProvider userId={volunteer} hideScore onRecorded={setSaved}>
              {(exercise.type === "reading" || exercise.type === "pacing") && (
                <PacingExercise key={attempt} sessionId={`${sessionId}-validation`} exercise={exercise} />
              )}
              {exercise.type === "picture" && <PictureDescriptionExercise key={attempt} exercise={exercise} />}
              {exercise.type === "words" && <WordPracticeExercise key={attempt} exercise={exercise} />}
              {exercise.type === "daf" && <DafExercise key={attempt} exercise={exercise} />}
            </PracticeHistoryProvider>

            {saved && (
              <Panel
                title="4 · Your rating"
                subtitle="Play the recording above, then rate the fluency of this attempt. The app's score appears after you submit."
              >
                {!submitted ? (
                  <div className="space-y-4">
                    <p className="flex items-center gap-2 rounded-lg bg-paper px-3 py-2 text-sm text-ink">
                      <Headphones size={16} className="text-teal-600" />
                      Listen to the whole recording before rating.
                    </p>
                    <RatingRow who={`Rater 1 — ${user?.name ?? "you"}`} value={rating1} onChange={setRating1} />
                    {secondRater.trim() && (
                      <RatingRow who={`Rater 2 — ${secondRater.trim()}`} value={rating2} onChange={setRating2} />
                    )}
                    <input
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder="Note (optional), e.g. two part-word repetitions on plosives"
                      className="w-full rounded-xl border border-teal-100 bg-white px-3 py-2 text-sm text-ink"
                    />
                    {error && <p className="text-sm text-red-700">{error}</p>}
                    <button
                      onClick={submit}
                      disabled={rating1 === null || (!!secondRater.trim() && rating2 === null)}
                      className="flex items-center gap-2 rounded-full bg-teal-600 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
                    >
                      <ClipboardCheck size={16} />
                      Submit rating
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-teal-200 bg-teal-50 p-4 text-sm text-teal-800">
                      <CheckCircle2 size={18} />
                      <span>
                        Rated {rating1}
                        {rating2 !== null ? ` and ${rating2}` : ""}. The app scored this attempt{" "}
                        <strong>{saved.score} / 100</strong> ({saved.verdict}).
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() => nextAttempt()}
                        className="flex items-center gap-1.5 rounded-full bg-teal-600 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-700"
                      >
                        <RotateCcw size={15} />
                        Next attempt (same exercise)
                      </button>
                      <button
                        onClick={() => nextAttempt(false)}
                        className="rounded-full border border-teal-200 px-5 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50"
                      >
                        Different exercise
                      </button>
                    </div>
                  </div>
                )}
              </Panel>
            )}
          </>
        )}
      </main>
    </AppShell>
  );
}
