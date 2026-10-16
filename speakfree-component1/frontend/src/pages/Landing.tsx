/**
 * Landing – public onboarding page for the whole SpeakFree project (all four features),
 * shown before sign-in. Content follows the SpeakFree pitch slides:
 *   hero → the problem → one platform for everyone (AI Analysis Engine) → the four features
 *   → how it works (screening → backend analysis → adaptive therapy) → trust & values → FAQs → CTA.
 *
 * Wording rule: only claim what exists. All four features are integrated and live (the
 * articulation and severity analysis run in the backend and are reviewed by the clinical admin);
 * numbers on the illustrative widgets are labelled "Sample".
 */
import { useEffect, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  AudioLines,
  Brain,
  BrainCircuit,
  CalendarX,
  ChartColumn,
  ChevronDown,
  CircleCheck,
  CircleHelp,
  ClipboardList,
  Clock,
  Gauge,
  Globe,
  HeartHandshake,
  HeartPulse,
  Hourglass,
  DollarSign,
  Lock,
  MessageCircleHeart,
  Mic,
  ScanText,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Target,
  TrendingUp,
  UserCog,
  Users,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import SiteFooter from "../components/SiteFooter";
import { Logo } from "../components/ui";

// =========================================================================== content (from the pitch slides)
const PROBLEMS: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <Clock size={22} />, title: "Long wait times", text: "More time, more delays." },
  { icon: <UserCog size={22} />, title: "Manual & difficult", text: "Requires expert effort and consistency." },
  { icon: <DollarSign size={22} />, title: "Costly process", text: "Higher operational and expert costs." },
  { icon: <Hourglass size={22} />, title: "High cost", text: "Expert time, manual scoring and administrative effort increase the cost." },
  { icon: <ClipboardList size={22} />, title: "Manual & prone to error", text: "Scoring depends on human judgment and is harder to standardise." },
  { icon: <Users size={22} />, title: "Resource intensive", text: "Requires trained professionals and more manpower." },
];

// Illustrative cost of one manual assessment, in US dollars (same proportions as the pitch slide).
const BILL: [string, number][] = [
  ["Consultation", 80],
  ["Assessment", 120],
  ["Manual scoring", 90],
  ["Report generation", 60],
];
const usd = (v: number) => `$${v.toLocaleString("en-US")}`;

const PILLS = ["AI-Powered", "Evidence-Based", "Explainable", "Accessible"];

type Tone = "brand" | "lav" | "navy" | "ok";
const TONE: Record<Tone, { badge: string; check: string; ring: string }> = {
  brand: { badge: "bg-brand-soft text-brand", check: "text-brand", ring: "hover:border-brand/40" },
  lav: { badge: "bg-lav-100 text-lav-600", check: "text-lav-600", ring: "hover:border-lav-400/60" },
  navy: { badge: "bg-[#E6EBF7] text-navy", check: "text-navy", ring: "hover:border-navy/40" },
  ok: { badge: "bg-ok-soft text-ok", check: "text-ok", ring: "hover:border-ok/40" },
};

const COMPONENTS: { n: number; title: string; icon: ReactNode; live: boolean; text: string; points: string[] }[] = [
  {
    n: 1, title: "Speech Screening & Feature Extraction", icon: <Mic size={20} />, live: true,
    text: "Noise-robust recording and Whisper-based transcription. Every word gets a confidence score – an objective marker of hesitation and unclear speech.",
    points: ["Age-matched tasks for ages 6–20", "Word-level ASR confidence", "Fluency, pronunciation & acoustic features"],
  },
  {
    n: 2, title: "Articulation Analysis", icon: <ScanText size={20} />, live: true,
    text: "An articulation score built from the word-level confidence of every recording – fillers removed, clear words counted, pooled across the whole session.",
    points: ["Articulation score per recording & session", "Fillers, repetitions, prolongations, long pauses"],
  },
  {
    n: 3, title: "Disorder & Severity Prediction", icon: <Gauge size={20} />, live: true,
    text: "A trained model cascade – including a dysarthria model built on the TORGO research corpus – suggests the likely disorder type and a 1–4 severity level for clinician review.",
    points: ["Disorder-type & severity models", "Confidence, uncertainty & explanation trail"],
  },
  {
    n: 4, title: "Adaptive Therapy & AI Assistant", icon: <HeartHandshake size={20} />, live: true,
    text: "A personal practice plan built from the screening that adapts after every exercise, with live coaching and an AI assistant for your focus area.",
    points: ["Adaptive plans, levels & goals", "Live coaching & AI practice assistant"],
  },
];

const STEPS: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <UserCog size={20} />, title: "Create a free account", text: "Enter the date of birth – SpeakFree picks tasks matched to one of seven age brackets (6–20 years)." },
  { icon: <Mic size={20} />, title: "Record three short tasks", text: "Describe a picture, talk through a scenario and answer a few questions – at home, in a few minutes." },
  { icon: <Sparkles size={20} />, title: "Press Analyse Now", text: "Every word is transcribed and scored, and acoustic features such as speaking rate and pauses are measured." },
  { icon: <Activity size={20} />, title: "Get your results & plan", text: "Clear results in plain words – then a personal therapy plan with daily exercises, live coaching and an AI assistant." },
];

const VALUES: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <Users size={22} />, title: "For every age", text: "Starting with ages 6–20" },
  { icon: <Globe size={22} />, title: "Accessible", text: "Anytime, anywhere" },
  { icon: <Target size={22} />, title: "Early detection", text: "Better outcomes" },
  { icon: <ShieldCheck size={22} />, title: "Evidence-based", text: "Built on speech research" },
  { icon: <Lock size={22} />, title: "Secure & private", text: "Raw audio never stored" },
  { icon: <HeartPulse size={22} />, title: "Empowering", text: "Better communication, better lives" },
];

const FAQS: { id?: string; q: string; a: string }[] = [
  { q: "Is SpeakFree a diagnosis?", a: "No. SpeakFree is a screening aid. Its results help families and clinicians decide on next steps, but they do not replace an assessment by a qualified speech-language pathologist." },
  { q: "Who can use SpeakFree?", a: "Young people aged 6–20 can screen themselves, parents and guardians can register a child, and clinicians can manage several patients and the task library." },
  { q: "How long does a screening take?", a: "Usually 5–15 minutes, depending on age: three short tasks – describe a picture, talk through a scenario and answer three questions. Each recording is analysed in a few seconds (the very first one can take a little longer)." },
  { q: "What happens to my recordings?", a: "Recordings stay in your own browser until you press Analyse Now. They are then analysed and deleted from the server straight away. Only the scores and transcript are stored, linked to a pseudonymous patient ID." },
  { q: "What happens after the screening?", a: "Your recordings are analysed further in the background (articulation and severity analysis, reviewed by our clinical team). You then get a personal therapy plan: short daily exercises that adapt to how you do, live coaching while you practise and an AI assistant to answer your questions. A new screening every few weeks updates the plan." },
  { q: "Does it cost anything?", a: "No. Creating an account, running a screening and using the therapy plan is free." },
  { id: "faq-accessibility", q: "Is SpeakFree accessible?", a: "SpeakFree runs in the web browser on computers and phones – there is no app to install. Forms and task choices can be used with the keyboard, pictures have text descriptions for screen readers, animations are reduced when your device asks for reduced motion, and you can upload an audio file instead of recording live." },
  { q: "What do I need?", a: "A device with a microphone and a quiet room. Browsers only allow microphone recording on secure (https) pages." },
];

// =========================================================================== hero illustration
function MicIllustration() {
  return (
    <svg viewBox="0 0 220 300" className="relative z-10 h-full w-auto drop-shadow-2xl" aria-hidden>
      <defs>
        <linearGradient id="mic-body" x1="0" x2="1">
          <stop offset="0" stopColor="#1B2559" />
          <stop offset="0.5" stopColor="#3B4A85" />
          <stop offset="1" stopColor="#141C44" />
        </linearGradient>
        <pattern id="mic-grille" width="7" height="7" patternUnits="userSpaceOnUse">
          <rect width="7" height="7" fill="#2A3566" />
          <circle cx="3.5" cy="3.5" r="1.6" fill="#7C86B8" />
        </pattern>
      </defs>
      <ellipse cx="110" cy="150" rx="70" ry="16" fill="none" stroke="#1B2559" strokeWidth="6" />
      <rect x="62" y="20" width="96" height="140" rx="48" fill="url(#mic-grille)" stroke="url(#mic-body)" strokeWidth="8" />
      <rect x="62" y="104" width="96" height="10" fill="#1B2559" />
      <rect x="78" y="160" width="64" height="40" rx="12" fill="url(#mic-body)" />
      <rect x="100" y="200" width="20" height="58" rx="6" fill="url(#mic-body)" />
      <ellipse cx="110" cy="272" rx="72" ry="16" fill="#141C44" />
      <ellipse cx="110" cy="266" rx="72" ry="14" fill="url(#mic-body)" />
      <ellipse cx="110" cy="266" rx="40" ry="5" fill="#7C6CF0" opacity="0.6" />
    </svg>
  );
}

function WaveBars({ count = 40, className = "" }: { count?: number; className?: string }) {
  return (
    <div className={`flex items-center gap-[3px] ${className}`} aria-hidden>
      {Array.from({ length: count }).map((_, i) => {
        const h = 12 + Math.abs(Math.sin(i * 0.7) * Math.cos(i * 0.23)) * 88;
        return <span key={i} className="w-[3px] rounded-full bg-white/90 shadow-[0_0_8px_rgba(124,108,240,0.8)]" style={{ height: `${h}%` }} />;
      })}
    </div>
  );
}

function FloatCard({ className, children }: { className: string; children: ReactNode }) {
  return <div className={`absolute z-20 rounded-2xl border border-white/70 bg-white/75 p-4 shadow-lift backdrop-blur ${className}`}>{children}</div>;
}

function HeroVisual() {
  const sample: [string, number][] = [["Fluency", 78], ["Pronunciation", 85], ["Voice Clarity", 92]];
  return (
    <div className="relative mx-auto aspect-[4/3.4] w-full max-w-[600px]">
      <div className="absolute inset-[12%] rounded-full bg-lav-400/25 blur-3xl" aria-hidden />
      {[0, 1, 2].map((i) => (
        <div key={i} className="absolute left-1/2 top-[44%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-lav-400/40"
          style={{ width: `${46 + i * 18}%`, aspectRatio: "1" }} aria-hidden />
      ))}
      <div className="absolute inset-x-[4%] top-[30%] h-[22%]">
        <WaveBars count={56} className="h-full justify-between" />
      </div>
      <div className="absolute inset-x-0 bottom-[2%] top-[8%] flex justify-center">
        <MicIllustration />
      </div>

      <FloatCard className="right-0 top-0 hidden w-48 md:block">
        <div className="text-[10px] font-bold uppercase tracking-wider text-ink-soft">Voice analysis · sample</div>
        <svg viewBox="0 0 120 20" className="my-2 w-full" aria-hidden>
          <path d="M0 10 Q5 2 10 10 T20 10 T30 10 T40 10 T50 10 T60 10 T70 10 T80 10 T90 10 T100 10 T110 10 T120 10" fill="none" stroke="#7C6CF0" strokeWidth="1.6" />
        </svg>
        {sample.map(([label, v]) => (
          <div key={label} className="mt-1.5">
            <div className="flex justify-between text-[11px] text-ink-soft"><span>{label}</span><span className="font-semibold text-ink">{v}%</span></div>
            <div className="mt-1 h-1.5 rounded-full bg-lav-100"><div className="h-1.5 rounded-full bg-gradient-to-r from-brand to-lav-500" style={{ width: `${v}%` }} /></div>
          </div>
        ))}
      </FloatCard>

      <FloatCard className="bottom-[10%] left-0 hidden w-44 md:block">
        <div className="text-[10px] font-bold uppercase tracking-wider text-ink-soft">Waveform analysis</div>
        <div className="my-2 h-7"><WaveBars count={22} className="h-full [&>span]:bg-lav-500 [&>span]:shadow-none" /></div>
        <div className="flex items-center gap-1.5 text-xs text-ink-soft"><CircleCheck size={14} className="text-ok" /> Normal pattern</div>
      </FloatCard>

      <FloatCard className="bottom-[22%] right-0 hidden w-44 md:block">
        <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-ink-soft"><Brain size={16} className="text-lav-500" /> AI insight</div>
        <p className="text-xs leading-snug text-ink-soft">Speech patterns analysed. Personalised therapy recommendations generated.</p>
      </FloatCard>

      <div className="absolute left-[14%] top-[6%] z-20 hidden h-12 w-12 place-items-center rounded-full border border-white/70 bg-white/70 text-lav-500 shadow-card backdrop-blur md:grid" aria-hidden>
        <AudioLines size={20} />
      </div>
      <div className="absolute bottom-[4%] right-[24%] z-20 hidden h-11 w-11 place-items-center rounded-full border border-white/70 bg-white/70 text-lav-500 shadow-card backdrop-blur md:grid" aria-hidden>
        <HeartPulse size={18} />
      </div>
    </div>
  );
}

// =========================================================================== platform (AI Analysis Engine hub)
function SampleTag() {
  return <span className="rounded-full bg-canvas px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-muted">Sample</span>;
}

function PillarCard({ icon, title, tone, points, children }: {
  icon: ReactNode; title: string; tone: Tone; points: string[]; children: ReactNode;
}) {
  const t = TONE[tone];
  return (
    <article className={`card flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-lift ${t.ring}`}>
      <div className="flex items-center gap-3">
        <span className={`grid h-11 w-11 place-items-center rounded-xl ${t.badge}`}>{icon}</span>
        <h3 className="text-lg font-bold text-ink">{title}</h3>
      </div>
      <ul className="mt-4 space-y-2 text-sm text-ink-soft">
        {points.map((p) => (
          <li key={p} className="flex items-start gap-2"><CircleCheck size={16} className={`mt-0.5 shrink-0 ${t.check}`} /> {p}</li>
        ))}
      </ul>
      <div className="mt-auto pt-5">{children}</div>
    </article>
  );
}

function EngineHub() {
  return (
    <div className="relative mx-auto grid aspect-square w-full max-w-[260px] place-items-center">
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-brand/15 to-lav-400/25 blur-xl" aria-hidden />
      <div className="absolute inset-0 rounded-full border-2 border-dashed border-lav-400/50 motion-safe:animate-[spin_40s_linear_infinite]" aria-hidden />
      <div className="relative grid h-[84%] w-[84%] place-items-center rounded-full border border-white bg-white/90 p-6 text-center shadow-lift">
        <div>
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand to-lav-500 text-white"><BrainCircuit size={30} /></span>
          <div className="mt-3 text-lg font-extrabold text-navy">AI Analysis Engine</div>
          <p className="mt-1 text-xs leading-snug text-ink-soft">Advanced speech AI for accurate screening, explainable insights and therapy guidance.</p>
        </div>
      </div>
    </div>
  );
}

function PlatformSection() {
  const patients = (
    <PillarCard icon={<Users size={22} />} title="Patients & Families" tone="brand"
      points={["Easy assessments from anywhere", "Early risk detection", "Clear insights and next steps", "Track progress over time"]}>
      <div className="rounded-xl border border-line bg-canvas/60 p-3">
        <div className="flex items-center justify-between text-xs font-semibold text-ink"><span>Assessment progress</span><SampleTag /></div>
        <div className="mt-2 flex items-center gap-2 text-xs text-ink-soft">
          <span className="h-2 w-2 rounded-full bg-bad motion-safe:animate-pulse" /> Recording… <span className="ml-auto font-mono">00:15</span>
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-brand-soft"><div className="h-1.5 w-2/3 rounded-full bg-brand" /></div>
      </div>
    </PillarCard>
  );
  const clinicians = (
    <PillarCard icon={<Stethoscope size={22} />} title="Therapists & Clinicians" tone="lav"
      points={["Comprehensive AI insights", "Explainable results", "Personalised therapy plans", "Track patient improvement"]}>
      <div className="flex items-center gap-3 rounded-xl border border-line bg-canvas/60 p-3">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full border-4 border-ok text-sm font-extrabold text-ink">87</div>
        <div className="text-xs"><div className="font-semibold text-ink">Patient insight</div><div className="text-ink-soft">ASR score · Good</div></div>
        <div className="ml-auto flex h-8 items-end gap-0.5" aria-hidden>
          {[40, 55, 45, 70, 60, 80, 75, 90].map((h, i) => <span key={i} className="w-1.5 rounded-sm bg-lav-500/70" style={{ height: `${h}%` }} />)}
        </div>
        <SampleTag />
      </div>
    </PillarCard>
  );
  const tech = (
    <PillarCard icon={<BrainCircuit size={22} />} title="AI Analysis & Technology" tone="navy"
      points={["Automatic speech recognition", "Articulation & fluency analysis", "Severity prediction", "Explainable AI models", "Research-backed algorithms"]}>
      <div className="grid grid-cols-5 gap-1.5 text-center text-[10px] font-medium leading-tight text-ink-soft">
        {[
          [<AudioLines size={18} key="a" />, "ASR"],
          [<ScanText size={18} key="p" />, "Phoneme analysis"],
          [<ChartColumn size={18} key="f" />, "Fluency metrics"],
          [<Gauge size={18} key="s" />, "Severity prediction"],
          [<Sparkles size={18} key="x" />, "Explainable AI"],
        ].map(([icon, label]) => (
          <div key={label as string} className="flex flex-col items-center gap-1 rounded-lg bg-canvas/70 px-1 py-2">
            <span className="text-navy">{icon}</span>{label}
          </div>
        ))}
      </div>
    </PillarCard>
  );
  const therapy = (
    <PillarCard icon={<MessageCircleHeart size={22} />} title="Therapy & Support" tone="ok"
      points={["Personalised therapy exercises", "Interactive & engaging tools", "Progress tracking", "Continuous support"]}>
      <div className="rounded-xl border border-line bg-canvas/60 p-3">
        <div className="flex items-center justify-between text-xs font-semibold text-ink"><span>Weekly progress</span><SampleTag /></div>
        <div className="mt-1 flex items-end gap-3">
          <svg viewBox="0 0 140 40" className="h-10 flex-1" aria-hidden>
            <polyline points="0,32 23,28 46,30 69,20 92,22 115,12 140,6" fill="none" stroke="#16A34A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            {[[0, 32], [23, 28], [46, 30], [69, 20], [92, 22], [115, 12], [140, 6]].map(([x, y]) => <circle key={x} cx={x} cy={y} r="2.5" fill="#16A34A" />)}
          </svg>
          <div className="text-right"><div className="flex items-center gap-1 text-lg font-extrabold text-ok"><TrendingUp size={16} /> +18%</div><div className="text-[10px] text-ink-muted">improvement</div></div>
        </div>
        <div className="mt-1 flex justify-between text-[9px] text-ink-muted">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => <span key={d}>{d}</span>)}</div>
      </div>
    </PillarCard>
  );

  return (
    <section id="platform" className="scroll-mt-20 py-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mx-auto max-w-3xl text-center">
          <div className="chip bg-lav-100 text-lav-600">One platform for everyone</div>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Connecting people. Enabling early detection.</h2>
          <p className="mt-3 text-ink-soft">Patients, families, clinicians and therapists work from the same explainable speech insights – powered by one AI analysis engine.</p>
        </div>
        <div className="mt-12 grid items-stretch gap-6 lg:grid-cols-[1fr_260px_1fr]">
          <div className="grid gap-6 lg:order-1">{patients}{tech}</div>
          <div className="flex items-center justify-center lg:order-2"><EngineHub /></div>
          <div className="grid gap-6 lg:order-3">{clinicians}{therapy}</div>
        </div>
      </div>
    </section>
  );
}

// =========================================================================== page
function TryButton({ className = "" }: { className?: string }) {
  return (
    <Link to="/login" className={`btn-primary gap-2 px-7 py-3.5 text-base shadow-nav ${className}`}>
      Try it for free <ArrowRight size={18} />
    </Link>
  );
}

export default function Landing() {
  const { user } = useAuth();
  const { hash } = useLocation();

  useEffect(() => {
    if (!hash) return;
    const el = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (!el) return;
    if (el instanceof HTMLDetailsElement) el.open = true;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [hash]);

  return (
    <div className="min-h-screen overflow-x-hidden bg-gradient-to-b from-[#F3F1FF] via-canvas to-canvas">
      {/* ------------------------------------------------------------- nav */}
      <header className="sticky top-0 z-40 border-b border-white/60 bg-white/70 backdrop-blur">
        <div className="mx-auto flex h-[72px] max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/welcome" aria-label="SpeakFree home"><Logo subtitle={false} /></Link>
          <nav className="hidden items-center gap-6 text-sm font-medium text-ink-soft lg:flex" aria-label="Page sections">
            <a href="#problem" className="hover:text-ink">The problem</a>
            <a href="#platform" className="hover:text-ink">Platform</a>
            <a href="#features" className="hover:text-ink">Features</a>
            <a href="#how" className="hover:text-ink">How it works</a>
            <a href="#trust" className="hover:text-ink">Trust</a>
            <a href="#faq" className="hover:text-ink">FAQs</a>
          </nav>
          {user ? (
            <Link to="/" className="btn-primary">Go to dashboard <ArrowRight size={16} /></Link>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="hidden px-3 py-2 text-sm font-semibold text-navy hover:underline sm:inline">Sign in</Link>
              <Link to="/login" className="btn-primary">Try it for free</Link>
            </div>
          )}
        </div>
      </header>

      {/* ------------------------------------------------------------- hero */}
      <section className="relative">
        <div className="absolute inset-x-0 bottom-0 h-40 bg-[radial-gradient(ellipse_at_bottom,rgba(124,108,240,0.18),transparent_70%)]" aria-hidden />
        <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-12 sm:px-6 lg:grid-cols-[1fr_1.05fr] lg:pt-16">
          <div>
            <h1 className="text-5xl font-extrabold tracking-tight text-navy sm:text-6xl lg:text-7xl">SpeakFree</h1>
            <div className="mt-5 flex items-center gap-1" aria-hidden>
              <span className="h-0.5 w-56 rounded-full bg-gradient-to-r from-navy to-lav-500" />
              <span className="h-2 w-2 rounded-full bg-lav-500" />
            </div>
            <p className="mt-5 max-w-md text-2xl font-medium leading-snug text-ink sm:text-[28px]">
              AI-Based Speech Disorder Screening and Therapy Assistant
            </p>
            <p className="mt-4 max-w-lg text-[15px] font-medium leading-relaxed text-navy">
              Connecting people. Enabling early detection. Empowering better speech health.
            </p>
            <ul className="mt-4 flex flex-wrap gap-2" aria-label="Principles">
              {PILLS.map((p) => <li key={p} className="chip border border-lav-200 bg-white/80 text-navy">{p}</li>)}
            </ul>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              {user ? <Link to="/" className="btn-primary px-7 py-3.5 text-base">Go to dashboard <ArrowRight size={18} /></Link> : <TryButton />}
              <a href="#platform" className="btn-ghost px-6 py-3.5 text-base">Explore the platform</a>
            </div>
            <div className="mt-8 inline-flex items-center gap-4 rounded-3xl bg-white/80 py-3 pl-3 pr-6 shadow-card">
              <span className="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-lav-400 to-navy text-white"><Brain size={22} /></span>
              <span className="text-[15px] font-medium leading-snug text-ink">Empowering Voices.<br />Enhancing Lives.</span>
            </div>
          </div>
          <HeroVisual />
        </div>
      </section>

      {/* ------------------------------------------------------------- problem */}
      <section id="problem" className="scroll-mt-20 bg-white/60 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid gap-10 lg:grid-cols-[1fr_1.2fr] lg:items-start">
            <div>
              <h2 className="text-3xl font-extrabold uppercase leading-tight tracking-tight text-navy sm:text-4xl">
                Manual speech screening is <span className="text-lav-600">slow, difficult &amp; expensive</span>
              </h2>
              <span className="mt-5 block h-0.5 w-40 rounded-full bg-lav-500" aria-hidden />
              <p className="mt-5 text-lg text-ink-soft">Delays in screening can delay better outcomes.</p>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <figure className="card p-5">
                  <figcaption className="text-xs font-bold uppercase tracking-wider text-ink-muted">A typical assessment bill</figcaption>
                  <dl className="mt-3 space-y-1.5 text-sm">
                    {BILL.map(([item, cost]) => (
                      <div key={item} className="flex justify-between text-ink-soft"><dt>{item}</dt><dd className="font-mono">{usd(cost)}</dd></div>
                    ))}
                    <div className="flex justify-between border-t border-line pt-2 font-bold text-ink">
                      <dt>Total</dt><dd className="font-mono text-bad">{usd(BILL.reduce((sum, [, c]) => sum + c, 0))}</dd>
                    </div>
                  </dl>
                </figure>
                <div className="card flex flex-col justify-center gap-4 p-5">
                  <div className="flex items-center gap-3">
                    <span className="grid h-11 w-11 place-items-center rounded-xl bg-lav-100 text-lav-600"><CalendarX size={22} /></span>
                    <div><div className="font-bold text-ink">Appointments full</div><div className="text-sm text-ink-soft">Next available: 2 weeks</div></div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="grid h-11 w-11 place-items-center rounded-xl bg-lav-100 text-lav-600"><Hourglass size={22} /></span>
                    <div><div className="font-bold text-ink">Long wait, longer process</div><div className="text-sm text-ink-soft">Please wait…</div></div>
                  </div>
                </div>
              </div>
            </div>

            <ul className="grid gap-4 sm:grid-cols-2">
              {PROBLEMS.map((p) => (
                <li key={p.title} className="card flex gap-4 p-5">
                  <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full border border-lav-200 bg-lav-50 text-lav-600">{p.icon}</span>
                  <div>
                    <div className="text-sm font-bold uppercase tracking-wide text-navy">{p.title}</div>
                    <p className="mt-1 text-sm leading-relaxed text-ink-soft">{p.text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- platform hub */}
      <PlatformSection />

      {/* ------------------------------------------------------------- four features */}
      <section id="features" className="scroll-mt-20 bg-white/60 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <div className="chip bg-lav-100 text-lav-600">Inside SpeakFree</div>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Four features, one journey</h2>
            <p className="mt-3 text-ink-soft">From the first recording to everyday therapy: each feature builds on the results of the one before it.</p>
          </div>
          <ol className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {COMPONENTS.map((c) => (
              <li key={c.n} className={`card relative flex flex-col p-6 ${c.live ? "ring-2 ring-brand/30" : ""}`}>
                <div className="flex items-center justify-between">
                  <span className={`grid h-11 w-11 place-items-center rounded-xl ${c.live ? "bg-brand text-white" : "bg-lav-100 text-navy"}`}>{c.icon}</span>
                  <span className={`chip ${c.live ? "bg-ok-soft text-ok" : "bg-canvas text-ink-muted"}`}>{c.live ? "Available now" : "Coming soon"}</span>
                </div>
                <div className="mt-4 text-xs font-bold uppercase tracking-wider text-lav-600">Feature {c.n}</div>
                <h3 className="mt-1 font-bold leading-snug text-ink">{c.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{c.text}</p>
                <ul className="mt-4 space-y-1.5 text-sm text-ink-soft">
                  {c.points.map((p) => <li key={p} className="flex items-start gap-2"><CircleCheck size={15} className="mt-0.5 shrink-0 text-lav-500" />{p}</li>)}
                </ul>
                {c.n < 4 && <ArrowRight size={18} className="absolute -right-4 top-1/2 z-10 hidden -translate-y-1/2 text-lav-400 xl:block" aria-hidden />}
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ------------------------------------------------------------- how it works */}
      <section id="how" className="scroll-mt-20 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <div className="chip bg-ok-soft text-ok">Available now</div>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">From a free screening to everyday therapy</h2>
            <p className="mt-3 text-ink-soft">No waiting room and no manual scoring. Screen at home in minutes, then practise with a plan that adapts to you.</p>
          </div>
          <ol className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="card relative p-6">
                <span className="absolute right-5 top-5 text-4xl font-extrabold text-lav-100" aria-hidden>{i + 1}</span>
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-navy text-white">{s.icon}</span>
                <h3 className="mt-4 font-bold text-ink">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ------------------------------------------------------------- trust & values */}
      <section id="trust" className="scroll-mt-20 bg-white/60 py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:items-center">
            <div>
              <h2 className="text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Built on trust. Driven by impact.</h2>
              <p className="mt-3 max-w-xl text-ink-soft">SpeakFree is committed to making speech healthcare accessible to every individual, every family, everywhere.</p>
            </div>
            <div className="card flex items-start gap-4 p-6">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-ok-soft text-ok"><ShieldCheck size={24} /></span>
              <div>
                <div className="text-sm font-bold text-ok">Privacy first · Secure · Ethical</div>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                  Recordings are deleted from the server right after analysis. Only derived scores and transcripts are kept,
                  linked to a pseudonymous patient ID. Each account sees only its own patients; only the SpeakFree administrator can review results across patients.
                </p>
              </div>
            </div>
          </div>
          <ul className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3 lg:grid-cols-6">
            {VALUES.map((v) => (
              <li key={v.title} className="flex flex-col items-center gap-2 bg-white p-5 text-center">
                <span className="text-navy">{v.icon}</span>
                <div className="text-sm font-bold text-ink">{v.title}</div>
                <div className="text-xs leading-snug text-ink-soft">{v.text}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ------------------------------------------------------------- FAQ */}
      <section id="faq" className="scroll-mt-20 py-20">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 sm:px-6 lg:grid-cols-[1fr_1.6fr]">
          <div>
            <div className="chip bg-lav-100 text-lav-600"><CircleHelp size={14} /> FAQs</div>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Questions, answered</h2>
            <p className="mt-3 text-ink-soft">Everything you need to know before your first screening.</p>
          </div>
          <div className="space-y-3">
            {FAQS.map((f) => (
              <details key={f.q} id={f.id} className="group card scroll-mt-24 p-0 open:shadow-lift">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 font-semibold text-ink [&::-webkit-details-marker]:hidden">
                  {f.q}
                  <ChevronDown size={18} className="shrink-0 text-ink-muted transition group-open:rotate-180" aria-hidden />
                </summary>
                <p className="px-5 pb-5 text-sm leading-relaxed text-ink-soft">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- final CTA */}
      <section className="px-4 py-20 sm:px-6">
        <div className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl bg-gradient-to-br from-navy-deep via-navy to-[#3B3FB6] px-6 py-14 text-center text-white sm:px-12">
          <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/5" aria-hidden />
          <div className="absolute -bottom-24 -left-10 h-72 w-72 rounded-full bg-lav-500/20" aria-hidden />
          <div className="relative">
            <h2 className="mx-auto max-w-3xl text-3xl font-extrabold tracking-tight sm:text-4xl">Together, let's build a world where every voice is heard and understood.</h2>
            <p className="mx-auto mt-3 max-w-xl text-white/75">Start with a free speech screening today – record three short tasks, get clear results in minutes and a therapy plan that grows with you.</p>
            <Link to={user ? "/" : "/login"} className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 text-base font-semibold text-navy hover:bg-lav-50">
              {user ? "Go to dashboard" : "Try it for free"} <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
