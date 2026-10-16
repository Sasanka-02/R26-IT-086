import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { ChatThread as Thread } from "../types/therapy";
import { getMessages, markMessagesRead, sendMessage } from "../therapy/therapyApi";

const REFRESH_MS = 15000;

function when(iso: string) {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/**
 * The conversation between one student and their therapists. Used by the
 * student (Messages page) and the therapist (student page). Messages are
 * marked read while the conversation is open, and it refreshes every 15 s.
 */
export default function ChatThread({
  student,
  viewerRole,
  onChange,
}: {
  student: string;
  viewerRole: "student" | "therapist";
  onChange?: () => void;
}) {
  const [thread, setThread] = useState<Thread | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const load = useCallback(async () => {
    try {
      const t = await getMessages(student);
      if (t.unread > 0) {
        setThread(await markMessagesRead(student));
        onChangeRef.current?.();
      } else {
        setThread(t);
      }
    } catch {
      setError("Couldn't load messages.");
    }
  }, [student]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread?.messages.length]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    setError(null);
    try {
      setThread(await sendMessage(student, text));
      setText("");
    } catch {
      setError("The message didn't send. Try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="max-h-[26rem] min-h-[10rem] space-y-2 overflow-y-auto rounded-xl bg-paper p-3">
        {thread && thread.messages.length === 0 && (
          <p className="py-8 text-center text-sm text-ink-soft">
            No messages yet.{" "}
            {viewerRole === "student"
              ? "Ask your therapist anything about your practice."
              : "Send a message to this student."}
          </p>
        )}
        {thread?.messages.map((m) => {
          const mine = m.from_role === viewerRole;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${
                  mine ? "bg-teal-600 text-white" : "border border-teal-100 bg-white text-ink"
                }`}
              >
                <p className="whitespace-pre-line">{m.text}</p>
                <p className={`mt-1 text-[11px] ${mine ? "text-white/75" : "text-ink-soft"}`}>
                  {mine ? "You" : m.from_name} · {when(m.at)}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="flex gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(e);
            }
          }}
          rows={2}
          maxLength={2000}
          placeholder="Write a message… (Enter to send, Shift+Enter for a new line)"
          className="min-w-0 flex-1 resize-none rounded-xl border border-teal-100 bg-white px-3 py-2 text-sm text-ink"
        />
        <button
          disabled={sending || !text.trim()}
          className="flex items-center gap-1.5 self-end rounded-full bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
        >
          <Send size={15} />
          Send
        </button>
      </form>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <p className="text-xs text-ink-soft">
        Messages are only visible to you and the clinic's therapists. For anything urgent, contact the clinic directly.
      </p>
    </div>
  );
}
