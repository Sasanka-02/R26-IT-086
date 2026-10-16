import AppShell from "../components/AppShell";
import ChatThread from "../components/ChatThread";
import { useAuth } from "../context/AuthContext";

/** Student: the conversation with their therapist. */
export default function MessagesPage() {
  const { user } = useAuth();
  return (
    <AppShell>
      <main className="mx-auto max-w-3xl space-y-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Messages</h1>
          <p className="mt-1 text-sm text-ink-soft">
            Ask your therapist a question or tell them how practice is going.
          </p>
        </div>
        <section className="rounded-2xl border border-snow/5 bg-white p-5">
          {user && (
            <ChatThread
              student={user.email}
              viewerRole="student"
              onChange={() => window.dispatchEvent(new Event("speakfree:messages-read"))}
            />
          )}
        </section>
      </main>
    </AppShell>
  );
}
