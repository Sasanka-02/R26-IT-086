import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Lightbulb, Medal, Play, Send, Target } from "lucide-react";
import { askAssistant, getAssistantBriefing } from "./therapyApi";
import { useAuth } from "../context/AuthContext";
import { usePracticeHistory } from "../context/PracticeHistoryContext";
import { AssistantAction, AssistantBriefing, AssistantReply } from "../types/therapy";

interface ChatMessage {
  from: "user" | "assistant";
  text: string;
  action?: AssistantAction | null;
  meta?: Pick<AssistantReply, "source" | "intent" | "confidence">;
}

function describeSource(meta: NonNullable<ChatMessage["meta"]>) {
  if (meta.source === "classifier") {
    return `Intent: ${meta.intent?.split("_").join(" ")} · ${Math.round(meta.confidence * 100)}% confident`;
  }
  if (meta.source === "llm") return "Answered by the AI language model (using only your practice summary)";
  return "Not confident — showing what I can help with";
}

interface AssistantPanelProps {
  onStart: (exerciseId: string) => void;
}

export default function AssistantPanel({ onStart }: AssistantPanelProps) {
  const { user } = useAuth();
  const { userId, version } = usePracticeHistory();
  const name = user?.name ?? "";
  const [briefing, setBriefing] = useState<AssistantBriefing | null>(null);
  const [error, setError] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    setError(false);
    getAssistantBriefing(userId, name)
      .then((data) => active && setBriefing(data))
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, [userId, name, version]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { from: "user", text: message }]);
    setSending(true);
    try {
      const reply = await askAssistant(userId, name, message);
      setMessages((prev) => [
        ...prev,
        {
          from: "assistant",
          text: reply.reply,
          action: reply.action,
          meta: { source: reply.source, intent: reply.intent, confidence: reply.confidence },
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { from: "assistant", text: "Sorry, I couldn't reach the therapy service just now." },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  if (error) {
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink">
        The assistant isn't available. Check that the therapy service is running.
      </p>
    );
  }
  if (!briefing) return <p className="text-sm text-ink-soft">Your assistant is getting ready...</p>;

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-teal-100 bg-white p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-teal-600 text-white">
            <Bot size={20} />
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">{briefing.greeting}</h2>
            <p className="text-xs text-ink-soft">Your personal practice assistant</p>
          </div>
        </div>
        <ul className="mt-4 space-y-2 text-sm text-ink">
          {briefing.summary.map((line) => (
            <li key={line} className="rounded-xl bg-paper px-4 py-2">
              {line}
            </li>
          ))}
        </ul>
      </div>

      {(briefing.goals.length > 0 || briefing.badges_total > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <div className="flex items-center gap-2">
              <Target size={18} className="text-teal-600" />
              <h3 className="text-sm font-semibold text-ink">Goals from your therapist</h3>
            </div>
            {briefing.goals.length === 0 ? (
              <p className="mt-2 text-sm text-ink-soft">No goals set yet.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm">
                {briefing.goals.map((g) => (
                  <li key={g.id} className={g.met ? "text-teal-800" : "text-ink"}>
                    {g.met ? "✓" : "○"} {g.text} <span className="text-ink-soft">(now {g.current ?? "—"})</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="rounded-2xl border border-teal-100 bg-white p-5">
            <div className="flex items-center gap-2">
              <Medal size={18} className="text-gold-500" />
              <h3 className="text-sm font-semibold text-ink">Badges</h3>
            </div>
            <p className="mt-2 text-sm text-ink">
              {briefing.badges_earned} of {briefing.badges_total} earned. Ask “What badges do I have?” to see
              which one is next.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-gold-400/60 bg-gold-400/10 p-5">
          <div className="flex items-center gap-2">
            <Lightbulb size={18} className="text-gold-600" />
            <h3 className="text-sm font-semibold text-ink">Today's focus: {briefing.focus.title}</h3>
          </div>
          <p className="mt-2 text-sm text-ink">{briefing.focus.tip}</p>
        </div>
        <div className="rounded-2xl border border-teal-200 bg-teal-50 p-5">
          <h3 className="text-sm font-semibold text-teal-800">Recommended next</h3>
          <p className="mt-1 text-sm font-medium text-ink">{briefing.next_step.title}</p>
          <p className="mt-1 text-sm text-ink-soft">{briefing.next_step.reason}</p>
          <button
            onClick={() => onStart(briefing.next_step.exercise_id)}
            className="mt-3 flex items-center gap-1.5 rounded-full bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
          >
            <Play size={14} />
            Start now
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-teal-100 bg-white p-5">
        <h3 className="text-base font-semibold text-ink">Ask your assistant</h3>
        <p className="mt-1 text-xs text-ink-soft">
          Questions are understood by a trained intent classifier
          {briefing.llm_enabled ? ", with an AI language model for anything it isn't sure about" : ""}.
          Answers use only your own practice data.
        </p>
        <div className="mt-3 max-h-80 space-y-3 overflow-y-auto">
          {messages.length === 0 && (
            <p className="text-sm text-ink-soft">
              Ask about your progress, what to practise, your level, or tips. Try one of the
              suggestions below.
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.from === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                  m.from === "user" ? "bg-teal-600 text-white" : "bg-paper text-ink"
                }`}
              >
                <p>{m.text}</p>
                {m.meta && <p className="mt-1 text-[11px] text-ink-soft">{describeSource(m.meta)}</p>}
                {m.action && (
                  <button
                    onClick={() => onStart(m.action!.exercise_id)}
                    className="mt-2 flex items-center gap-1 rounded-full bg-teal-600 px-3 py-1 text-xs font-medium text-white hover:bg-teal-700"
                  >
                    <Play size={12} />
                    {m.action.label}
                  </button>
                )}
              </div>
            </div>
          ))}
          {sending && <p className="text-xs text-ink-soft">Assistant is typing...</p>}
          <div ref={endRef} />
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {briefing.suggestions.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="rounded-full border border-teal-200 px-3 py-1 text-xs text-teal-700 hover:bg-teal-50"
            >
              {s}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a question..."
            className="flex-1 rounded-full border border-teal-100 px-4 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="flex items-center gap-1 rounded-full bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
          >
            <Send size={14} />
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
