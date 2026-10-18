/**
 * AssistantPage – the category-aware AI practice assistant (Component 4).
 * Answers come from the patient's own plan and results (intent classifier); open questions go to
 * an optional Claude model with a focus-specific prompt. Never shows a diagnosis.
 * The backend sets the tone by age bracket (ages 6–9 playful … 21+ respectful); the chat's look follows it.
 */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bot, Lightbulb, Loader2, Send, Sparkles } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { ErrorBox, Spinner } from "../../components/ui";
import type { Briefing, ChatReply } from "../../types/integration";

interface Msg { who: "me" | "bot"; text: string; action?: ChatReply["action"] }

export default function AssistantPage() {
  const { activePatient } = useAuth();
  const [brief, setBrief] = useState<Briefing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [noPlan, setNoPlan] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activePatient) return;
    setBrief(null); setNoPlan(false); setMsgs([]);
    api.therapy.briefing(activePatient.id).then((b) => { setBrief(b); setSuggestions(b.suggestions); })
      .catch((e: Error & { status?: number }) => (e.status === 404 ? setNoPlan(true) : setError(e.message)));
  }, [activePatient]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [msgs]);

  async function ask(question: string) {
    if (!activePatient || !question.trim() || busy) return;
    setMsgs((m) => [...m, { who: "me", text: question }]);
    setText("");
    setBusy(true);
    try {
      const r = await api.therapy.chat(activePatient.id, question.trim());
      setMsgs((m) => [...m, { who: "bot", text: r.reply, action: r.action }]);
      setSuggestions(r.suggestions);
    } catch (e) {
      setMsgs((m) => [...m, { who: "bot", text: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (error) return <ErrorBox message={error} />;
  if (noPlan) return (
    <div className="card mx-auto max-w-xl p-8 text-center">
      <Bot className="mx-auto text-navy" size={36} />
      <h1 className="mt-3 text-xl font-extrabold">Your assistant is ready after your first screening</h1>
      <Link to="/assessment" className="btn-primary mt-5">Start the screening <ArrowRight size={15} /></Link>
    </div>
  );
  if (!brief) return <Spinner />;
  const playful = brief.tone === "playful";
  const bubble = playful ? "text-base" : "text-sm";

  return (
    // ★ NOVELTY (Component 4): category-aware AI assistant – answers use the patient's own therapy focus
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <section className="card flex min-h-[560px] flex-col">
        <header className="flex items-center gap-3 border-b border-line p-5">
          <span className={`grid h-11 w-11 place-items-center rounded-2xl text-white ${playful ? "bg-sun text-2xl" : "bg-navy"}`}>{playful ? "🦉" : <Bot size={22} />}</span>
          <div>
            <h1 className="text-lg font-extrabold">{playful ? "Your practice buddy" : "Practice assistant"}</h1>
            <p className="text-xs muted">Coaching for “{brief.focus.name}” {brief.llm_enabled && <span className="chip ml-1 bg-lav-100 px-2 py-0 text-[10px] text-lav-600"><Sparkles size={10} /> AI</span>}</p>
          </div>
        </header>
        <div className="flex-1 space-y-3 overflow-y-auto p-5 scrollbar-thin" aria-live="polite">
          <div className={`max-w-[85%] rounded-2xl rounded-tl-sm bg-lav-50 p-4 text-ink ${bubble}`}>
            <p className="font-bold">{brief.greeting}</p>
            {brief.summary.map((l) => <p key={l} className="mt-1">{l}</p>)}
          </div>
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.who === "me" ? "justify-end" : ""}`}>
              <div className={`max-w-[85%] rounded-2xl p-3 ${bubble} ${m.who === "me" ? "rounded-tr-sm bg-navy text-white" : "rounded-tl-sm bg-lav-50 text-ink"}`}>
                {m.text}
                {m.action && (
                  <Link to={m.action.href ?? `/therapy/exercise/${m.action.exercise_id}`} className="mt-2 flex items-center gap-1 text-xs font-semibold text-brand hover:underline">
                    {m.action.label} <ArrowRight size={12} />
                  </Link>
                )}
              </div>
            </div>
          ))}
          {busy && <Loader2 className="animate-spin text-brand" size={18} />}
          <div ref={endRef} />
        </div>
        <div className="border-t border-line p-4">
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.map((s) => <button key={s} className={`btn-lav ${playful ? "px-4 py-2.5 text-sm" : "px-3 py-1.5 text-xs"}`} onClick={() => void ask(s)} disabled={busy}>{s}</button>)}
          </div>
          <form className="flex gap-2" onSubmit={(e: FormEvent) => { e.preventDefault(); void ask(text); }}>
            <input className="input" value={text} maxLength={500} onChange={(e) => setText(e.target.value)} placeholder="Ask about your practice…" aria-label="Message" />
            <button className="btn-primary px-4" disabled={busy || !text.trim()} aria-label="Send"><Send size={16} /></button>
          </form>
        </div>
      </section>

      <aside className="space-y-4">
        <div className="card p-5">
          <h2 className="flex items-center gap-2 font-bold"><Lightbulb size={18} className="text-sun" /> Tip for you</h2>
          <p className="mt-2 text-sm text-ink-soft">{brief.tip}</p>
        </div>
        <div className="card p-5">
          <h2 className="font-bold">Up next</h2>
          <p className="mt-1 text-sm font-semibold text-ink">{brief.next_step.title}</p>
          <p className="mt-1 text-xs muted">{brief.next_step.reason}</p>
          <Link to={`/therapy/exercise/${brief.next_step.exercise_id}`} className="btn-primary mt-3 w-full">Start <ArrowRight size={15} /></Link>
        </div>
        <div className="card p-5">
          <h2 className="font-bold">Techniques</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-soft">{brief.focus.techniques.map((t) => <li key={t}>{t}</li>)}</ul>
        </div>
      </aside>
    </div>
  );
}
