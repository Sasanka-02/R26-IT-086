/**
 * ListenButton – "🔊 Listen": the browser reads a prompt or a reading model aloud (speechSynthesis).
 * Used for ages 6–11 (playful theme) in the screening tasks and the therapy exercises.
 * Nothing is recorded or sent anywhere.
 */
import { useEffect, useState } from "react";
import { Volume2 } from "lucide-react";

export default function ListenButton({ text, wpm, big = false }: { text: string; wpm?: number; big?: boolean }) {
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => () => window.speechSynthesis?.cancel(), []);
  if (typeof window === "undefined" || !("speechSynthesis" in window) || !text.trim()) return null;
  const toggle = () => {
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-GB";
    u.rate = Math.max(0.6, Math.min(1, (wpm ?? 120) / 150)); // a slow, clear model
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
    setSpeaking(true);
  };
  return (
    <button type="button" onClick={toggle} className={`btn-lav ${big ? "px-5 py-3 text-base" : "px-3 py-1.5 text-sm"}`} aria-pressed={speaking}>
      <Volume2 size={big ? 20 : 15} /> {speaking ? "Stop" : "🔊 Listen"}
    </button>
  );
}
