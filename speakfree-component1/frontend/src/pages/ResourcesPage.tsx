/**
 * ResourcesPage – plain-language guides for patients and families. The guide for the patient's
 * own therapy focus (from their plan) is shown first.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Ear, HeartHandshake, Mic, Sparkles, Users, Wind } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Focus, PlanResponse } from "../types/integration";

interface Guide { key: string; focus?: Focus; icon: ReactNode; title: string; intro: string; tips: string[] }

const GUIDES: Guide[] = [
  { key: "fluency", focus: "fluency", icon: <Wind size={20} />, title: "Smooth, confident speech",
    intro: "Techniques that make words flow more easily and help when speech gets stuck.",
    tips: ["Start each sentence on a slow breath out with a soft, easy first sound.",
      "Slow down a little and pause on purpose between ideas – pauses are a tool, not a mistake.",
      "Touch the lips and tongue together lightly on hard sounds like p, b, t and d.",
      "If a word gets stuck, stop, breathe, and slide gently into it again."] },
  { key: "motor", focus: "motor_speech", icon: <Mic size={20} />, title: "A clear, strong voice",
    intro: "Breath support and clear, deliberate movements help people understand you the first time.",
    tips: ["Take a full breath before each phrase and keep phrases short.",
      "“Think loud”: imagine speaking to someone across the room – strong, not shouting.",
      "Move your lips, tongue and jaw a little more than feels normal.",
      "Give every syllable its own beat, especially at the end of words."] },
  { key: "sounds", focus: "speech_sounds", icon: <Sparkles size={20} />, title: "Crisp speech sounds",
    intro: "Short, focused practice on the exact sounds that are tricky works best.",
    tips: ["Practise the sound on its own, then in words, phrases and sentences.",
      "Use a mirror to watch where your lips and tongue go.",
      "Go slowly and accurately first – speed comes later.",
      "Five minutes every day beats one long session a week."] },
  { key: "maintain", focus: "maintenance", icon: <BookOpen size={20} />, title: "Keep your speech sharp",
    intro: "Light, regular practice keeps speech confident and clear.",
    tips: ["Read aloud with expression for a few minutes a day.", "Describe pictures, your day or a film in full sentences.",
      "Keep a natural, relaxed pace and make eye contact."] },
  { key: "family", icon: <Users size={20} />, title: "For parents & families",
    intro: "Small changes at home make a big difference.",
    tips: ["Give your child time to finish – don't finish words or sentences for them.",
      "Speak a little more slowly yourself; children copy the pace around them.",
      "Praise effort and practice, not just “perfect” words.",
      "Keep practice short, fun and at a regular time each day."] },
  { key: "when", icon: <Ear size={20} />, title: "When to see a speech-language pathologist",
    intro: "SpeakFree is a screening and practice aid – it does not replace a professional assessment.",
    tips: ["Speech difficulties that worry you, your child or teachers.",
      "Avoiding speaking situations, or frustration or anxiety about speaking.",
      "No improvement after several weeks of regular practice.",
      "Any sudden change in speech – seek medical advice promptly."] },
];

export default function ResourcesPage() {
  const { activePatient } = useAuth();
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  useEffect(() => {
    if (activePatient) api.therapy.plan(activePatient.id).then(setPlan).catch(() => setPlan(null));
  }, [activePatient]);
  const focus = plan?.has_profile ? plan.focus.key : null;
  const guides = [...GUIDES].sort((a, b) => Number(b.focus === focus) - Number(a.focus === focus));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Resources</h1>
        <p className="mt-1 text-sm text-ink-soft">Practical guides for practising at home{focus ? " – starting with the one for your plan" : ""}.</p>
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        {guides.map((g) => {
          const mine = g.focus && g.focus === focus;
          return (
            <article key={g.key} className={`card p-6 ${mine ? "ring-2 ring-brand/40" : ""}`}>
              <div className="flex items-center gap-3">
                <span className={`grid h-11 w-11 place-items-center rounded-xl ${mine ? "bg-navy text-white" : "bg-lav-100 text-navy"}`}>{g.icon}</span>
                <div>
                  <h2 className="font-bold text-ink">{g.title}</h2>
                  {mine && <span className="chip mt-1 bg-brand-soft px-2 py-0.5 text-[11px] text-navy">Your plan</span>}
                </div>
              </div>
              <p className="mt-3 text-sm text-ink-soft">{g.intro}</p>
              <ul className="mt-3 space-y-2 text-sm text-ink">{g.tips.map((t) => <li key={t} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-lav-500" />{t}</li>)}</ul>
            </article>
          );
        })}
      </div>
      <section className="flex flex-col gap-4 rounded-2xl bg-brand-soft p-6 sm:flex-row sm:items-center">
        <HeartHandshake className="text-navy" size={28} />
        <p className="flex-1 text-sm text-ink">Questions about your practice? Ask the AI assistant, or request a session with a speech-language pathologist.</p>
        <div className="flex gap-2">
          <Link to="/therapy/assistant" className="btn-outline">AI assistant</Link>
          <Link to="/appointments" className="btn-primary">Book a session</Link>
        </div>
      </section>
    </div>
  );
}
