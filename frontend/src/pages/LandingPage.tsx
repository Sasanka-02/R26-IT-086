import { useNavigate } from "react-router-dom";
import { Mic, ShieldCheck, Gauge, MessagesSquare, ArrowRight } from "lucide-react";
import WaveformArt from "../components/WaveformArt";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-paper">
      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-600 text-white">
            <Mic size={16} />
          </div>
          <span className="font-display text-lg font-semibold text-ink">SpeakFree</span>
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

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl gap-10 px-6 py-14 sm:py-20 lg:grid-cols-2 lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-600">
            Speech screening, listened carefully
          </p>
          <h1 className="mt-4 font-display text-4xl font-semibold leading-tight text-ink sm:text-5xl">
            We listen closely,
            <br />
            <span className="italic text-teal-600">so you don't have to wait.</span>
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-ink-soft">
            A free, private, browser-based screening for speech disorders —
            three short tasks, no appointment, no downloads. Built to stay
            accurate even in noisy, real-world conditions.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              onClick={() => navigate("/signup")}
              className="inline-flex items-center gap-2 rounded-full bg-teal-600 px-6 py-3 text-sm font-semibold text-white hover:bg-teal-700"
            >
              Begin Screening
              <ArrowRight size={16} />
            </button>
            <span className="text-sm text-ink-soft">Takes about 5 minutes</span>
          </div>
        </div>

        <div className="rounded-3xl border border-teal-100 bg-white p-8 shadow-sm">
          <p className="text-sm font-medium text-ink-soft">Live waveform, as it sounds to us</p>
          <div className="mt-6 h-28">
            <WaveformArt className="h-full w-full" />
          </div>
          <div className="mt-6 grid grid-cols-3 gap-3 text-center">
            <div className="rounded-xl bg-teal-50 py-3">
              <p className="font-display text-xl font-semibold text-teal-700">3</p>
              <p className="text-xs text-ink-soft">short tasks</p>
            </div>
            <div className="rounded-xl bg-teal-50 py-3">
              <p className="font-display text-xl font-semibold text-teal-700">0</p>
              <p className="text-xs text-ink-soft">recordings stored</p>
            </div>
            <div className="rounded-xl bg-teal-50 py-3">
              <p className="font-display text-xl font-semibold text-teal-700">~5</p>
              <p className="text-xs text-ink-soft">minutes total</p>
            </div>
          </div>
        </div>
      </section>

      <div className="waveform-divider mx-6" />

      {/* How it works — genuine 3-step sequence, so numbering is earned */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="font-display text-2xl font-semibold text-ink sm:text-3xl">
          How the screening works
        </h2>
        <p className="mt-2 max-w-xl text-ink-soft">
          Three tasks, each capturing a different way speech naturally varies.
        </p>

        <div className="mt-10 grid gap-8 sm:grid-cols-3">
          {[
            {
              step: "01",
              title: "Describe a picture",
              body: "Look at an image and describe what's happening, at your own pace.",
            },
            {
              step: "02",
              title: "Narrate a video",
              body: "Watch a short silent clip, then tell us what happened.",
            },
            {
              step: "03",
              title: "Answer a few questions",
              body: "A short guided conversation, tailored to your age group.",
            },
          ].map((s) => (
            <div key={s.step} className="border-t-2 border-teal-600 pt-4">
              <span className="font-display text-3xl font-semibold text-teal-600/30">
                {s.step}
              </span>
              <h3 className="mt-2 font-display text-lg font-semibold text-ink">{s.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="waveform-divider mx-6" />

      {/* Feature grid */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-6 sm:grid-cols-3">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <Gauge className="text-teal-600" size={22} />
            <h3 className="mt-3 font-display font-semibold text-ink">
              Noise-robust analysis
            </h3>
            <p className="mt-1 text-sm text-ink-soft">
              Confidence-aware speech recognition designed to stay reliable
              even with background noise and variable speech.
            </p>
          </div>
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <MessagesSquare className="text-teal-600" size={22} />
            <h3 className="mt-3 font-display font-semibold text-ink">
              Three-task screening
            </h3>
            <p className="mt-1 text-sm text-ink-soft">
              Picture description, video narration, and a short guided
              conversation — capturing patterns a single task would miss.
            </p>
          </div>
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <ShieldCheck className="text-teal-600" size={22} />
            <h3 className="mt-3 font-display font-semibold text-ink">
              Privacy-first
            </h3>
            <p className="mt-1 text-sm text-ink-soft">
              Audio is processed for this session only — no permanent
              storage of your recordings.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-teal-100 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-600 text-white">
              <Mic size={13} />
            </div>
            <span className="font-display font-semibold text-ink">SpeakFree</span>
          </div>
          <p className="mt-3 max-w-md text-sm text-ink-soft">
            Not a replacement for a licensed speech-language pathologist —
            this screening is a first step, not a diagnosis.
          </p>
        </div>
      </footer>
    </div>
  );
}