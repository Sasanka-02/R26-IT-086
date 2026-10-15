import { useNavigate } from "react-router-dom";
import { HeartPulse, ShieldCheck, Gauge, Sparkles, ArrowRight } from "lucide-react";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-shell">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-600 text-white">
            <HeartPulse size={16} />
          </div>
          <span className="font-display text-lg font-semibold text-ink">
            SpeakFree Therapy
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className="text-sm font-medium text-ink-soft hover:text-ink"
          >
            Log in
          </button>
          <button
            onClick={() => navigate("/signup")}
            className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
          >
            Get Started
          </button>
        </div>
      </header>

      <section className="mx-auto max-w-3xl px-6 py-16 text-center sm:py-20">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-600">
          AI Therapy Assistant
        </p>
        <h1 className="mt-4 font-display text-4xl font-semibold leading-tight text-ink sm:text-5xl">
          Practice speech therapy,
          <br />
          <span className="italic text-teal-600">on your own time.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-ink-soft">
          Real-time pacing coaching, delayed auditory feedback, and guided
          picture-description practice — with a privacy-preserving design
          throughout, from local-only audio processing to a transparent
          differential-privacy budget.
        </p>
        <button
          onClick={() => navigate("/signup")}
          className="mt-8 inline-flex items-center gap-2 rounded-full bg-teal-600 px-6 py-3 text-base font-semibold text-white hover:bg-teal-700"
        >
          Start Practicing
          <ArrowRight size={16} />
        </button>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-6 sm:grid-cols-3">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <Gauge className="text-teal-600" size={22} />
            <h3 className="mt-3 font-display font-semibold text-ink">
              Real-time coaching
            </h3>
            <p className="mt-1 text-sm text-ink-soft">
              Live pacing cues while you read, computed entirely from
              on-device audio metrics — never raw audio.
            </p>
          </div>
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <Sparkles className="text-teal-600" size={22} />
            <h3 className="mt-3 font-display font-semibold text-ink">
              Adaptive weekly plans
            </h3>
            <p className="mt-1 text-sm text-ink-soft">
              A contextual bandit selects your next week's exercises based
              on how recent sessions actually went.
            </p>
          </div>
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <ShieldCheck className="text-teal-600" size={22} />
            <h3 className="mt-3 font-display font-semibold text-ink">
              Transparent privacy budget
            </h3>
            <p className="mt-1 text-sm text-ink-soft">
              Your voice never leaves your device. Statistics shared outside
              the clinic carry differential-privacy noise, and the budget
              spent is always visible.
            </p>
          </div>
        </div>
      </section>

      <footer className="border-t border-teal-100 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-600 text-white">
              <HeartPulse size={13} />
            </div>
            <span className="font-display font-semibold text-ink">SpeakFree Therapy</span>
          </div>
          <p className="mt-3 max-w-md text-sm text-ink-soft">
            A supplementary practice tool, not a replacement for a licensed
            speech-language pathologist.
          </p>
        </div>
      </footer>
    </div>
  );
}
