/**
 * TherapyMonitor (admin) – ★ Component 4 novelty, explained for one patient:
 * the C3-derived profile, the learner's age bracket and practice level (with the therapist's
 * override + exercise assignment), the LinUCB bandit's current ranking (exploit + explore +
 * category prior + difficulty fit), goals, every attempt and the AI-assistant log.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Bot, CalendarRange, Cpu, History, Loader2, Target, TrendingUp, UserCog } from "lucide-react";
import { api } from "../../../api/client";
import { Card, COLORS, ErrorBox, Spinner } from "../../../components/ui";
import { FOCUS_LABEL, SeverityChip, StatTile, TrendLine } from "../../../components/charts";
import type { AdminTherapy } from "../../../types/integration";
import { BRACKETS } from "../../../utils/age";

const pctN = (v: number | null | undefined) => (v === null || v === undefined ? "–" : String(v));

export default function TherapyMonitor() {
  const { patientId = "" } = useParams();
  const [data, setData] = useState<AdminTherapy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const load = useCallback(() => api.admin.therapy(patientId).then(setData).catch((e: Error) => setError(e.message)), [patientId]);
  useEffect(() => { void load(); }, [load]);

  async function saveSettings(body: Parameters<typeof api.admin.therapySettings>[1]) {
    setSaving(true);
    try {
      await api.admin.therapySettings(patientId, body);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner />;
  const { profile, plan, patient } = data;
  const assigned = new Set(patient.assigned_exercises);
  const toggleAssign = (id: string) =>
    void saveSettings({ assigned_exercise_ids: assigned.has(id) ? [...assigned].filter((x) => x !== id) : [...assigned, id] });

  return (
    <div className="space-y-6">
      <Link to={`/admin/patients/${patientId}`} className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> Patient profile</Link>
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Therapy monitor · {data.patient.full_name}</h1>
        <p className="text-sm text-ink-soft">
          Age {patient.age ?? "not given yet"}{patient.age_bracket ? ` · age bracket ${patient.age_bracket.id} (${patient.age_bracket.label})` : ""}
          {patient.age_bracket_override ? ` · practice level pinned to ${patient.age_bracket_override} by a therapist` : ""}
        </p>
        <p className="text-sm text-ink-soft">Component 4 – adaptive therapy plan and AI assistant, driven by the latest Component 3 result.</p>
      </div>

      {!profile || !plan ? (
        <div className="card p-8 text-center text-sm muted">No therapy profile yet – the patient has not completed a screening.</div>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Therapy focus" value={<span className="text-xl">{FOCUS_LABEL[profile.focus]}</span>} sub={`patient sees: “${profile.focus_name}”`} />
            <StatTile label="C3 severity" value={<SeverityChip level={profile.severity_level} />} sub={`start level ${profile.start_level}`} />
            <StatTile label="Practice level" value={`${plan.level.label}${plan.level.override ? " (therapist)" : ""}`} sub={`${plan.level.ages} tasks · ${plan.level.progress_text}`} />
            <StatTile label="Exercises done" value={plan.progress.total_sessions} sub={`avg ${pctN(plan.progress.average_score)} · streak ${plan.progress.streak_days} d`} />
          </section>

          <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <Card title="Score trend" icon={<TrendingUp size={18} className="text-navy" />}>
              <TrendLine threshold={{ value: plan.level.strong_threshold, label: `strong ≥ ${plan.level.strong_threshold}` }}
                points={plan.progress.history.map((h) => ({ x: String(h.attempt), y: h.score, label: `${h.title} · ${new Date(h.completed_at).toLocaleDateString()}` }))} />
            </Card>
            <Card title="Goals" icon={<Target size={18} className="text-navy" />}>
              <ul className="space-y-2 text-sm">
                {plan.goals.map((g) => (
                  <li key={g.id} className="flex items-start justify-between gap-3">
                    <span className={g.met ? "text-ink" : "text-ink-soft"}>{g.met ? "✓ " : ""}{g.text}</span>
                    <span className="shrink-0 font-mono text-xs">{pctN(g.current)} / {g.target}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 rounded-lg bg-lav-50 p-2 text-xs text-ink-soft">
                Re-screening {plan.rescreen.recommended ? `recommended now (${plan.rescreen.reasons.join(", ")})` : `due in ${plan.rescreen.due_in_days} days or ${plan.rescreen.attempts_until_due} exercises`}.
              </p>
            </Card>
          </section>

          {/* ★ NOVELTY (Component 4): age-bracketed therapy – the therapist can pin the level and assign exercises */}
          <Card title="Age bracket & practice level (therapist controls)" icon={<UserCog size={18} className="text-navy" />}
            right={saving ? <Loader2 size={16} className="animate-spin text-brand" /> : undefined}>
            <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
              <div className="space-y-2 text-sm">
                <p><b>Age bracket:</b> {patient.age_bracket ? `${patient.age_bracket.id} · ${patient.age_bracket.label}` : "unknown"} · tone <b>{plan.learner.tone}</b> · look <b>{plan.learner.theme}</b></p>
                <p><b>Start:</b> Level {plan.level.start_bracket} {plan.level.start_bracket < plan.level.age_bracket ? "(severe screening → one level below age)" : "(age bracket)"} · allowed range Level {plan.level.min_bracket}–{plan.level.max_bracket} (age bracket + 1)</p>
                <p className="rounded-lg bg-lav-50 p-2 text-xs text-ink-soft">Patient sees: “{plan.level.dashboard_text}”</p>
              </div>
              <div className="space-y-3">
                <label className="block text-sm">
                  <span className="label">Practice level</span>
                  <select className="input py-2" value={patient.age_bracket_override ?? ""} disabled={saving}
                    onChange={(e) => void saveSettings({ age_bracket_override: e.target.value ? Number(e.target.value) : null })}>
                    <option value="">Adaptive – 2 strong ↑ / 2 difficult ↓ (now Level {plan.level.override ? "–" : plan.level.bracket})</option>
                    {BRACKETS.map((b) => <option key={b.id} value={b.id}>Pin Level {b.id} · {b.label}</option>)}
                  </select>
                </label>
                <p className="text-xs muted">Assigned exercises ({assigned.size}) always come first in the patient's plan – tick them in the ranking table below.</p>
              </div>
            </div>
          </Card>

          {/* ★ NOVELTY (Component 4): LinUCB contextual bandit with the Component 3 category prior */}
          <Card title="Adaptive engine – LinUCB ranking with the C3 category prior" icon={<Cpu size={18} className="text-navy" />}>
            <div className="mb-3 flex flex-wrap gap-2 text-xs">
              {plan.engine.context.labels.map((l, i) => (
                <span key={l} className="chip bg-lav-50 font-mono text-ink">{l} = {plan.engine.context.vector[i].toFixed(2)}</span>
              ))}
            </div>
            <p className="mb-3 font-mono text-xs text-ink-soft">rank = θᵀx (exploit) + α√(xᵀA⁻¹x) (explore) + β(2·fit − 1) (C3 prior) − 0.1·|difficulty − tier(bracket)| · bracket tasks share one arm per type</p>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-sm">
                <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide muted">
                  <th className="py-2">#</th><th>Exercise</th><th>Tried</th><th>Exploit</th><th>Explore</th><th>C3 fit</th><th>Prior</th><th>Difficulty</th><th>Total</th><th>Assign</th>
                </tr></thead>
                <tbody className="divide-y divide-line">
                  {plan.engine.arms.map((a) => {
                    const today = plan.today.some((t) => t.id === a.id);
                    return (
                      <tr key={a.id} className={today ? "bg-brand-soft/60" : ""}>
                        <td className="py-1.5 font-mono text-xs">{a.rank}</td>
                        <td><span className="font-semibold text-ink">{a.title}</span>{a.bracket && <span className="chip ml-2 bg-brand-soft px-2 py-0.5 text-[10px] text-navy">L{a.bracket} {a.task_type}</span>}{today && <span className="chip ml-2 bg-navy px-2 py-0.5 text-[10px] text-white">today</span>}</td>
                        <td className="font-mono">{a.times_practised}</td>
                        <td className="font-mono">{a.expected_reward.toFixed(3)}</td>
                        <td className="font-mono">{a.exploration_bonus.toFixed(3)}</td>
                        <td className="font-mono">{a.category_fit.toFixed(2)}</td>
                        <td className="font-mono" style={{ color: a.category_prior >= 0 ? COLORS.ok : COLORS.bad }}>{a.category_prior >= 0 ? "+" : ""}{a.category_prior.toFixed(3)}</td>
                        <td className="font-mono">{a.difficulty_fit.toFixed(2)}</td>
                        <td className="font-mono font-bold">{a.total.toFixed(3)}</td>
                        <td><input type="checkbox" className="h-4 w-4 accent-[#1E3A8A]" checked={assigned.has(a.id)} disabled={saving}
                          onChange={() => toggleAssign(a.id)} aria-label={`Assign ${a.title}`} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <section className="grid gap-5 lg:grid-cols-2">
            <Card title="Level history (age-bracket ladder)" icon={<History size={18} className="text-navy" />}>
              <ol className="space-y-2 text-sm">
                {plan.level.history.map((h, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: h.direction === "down" ? COLORS.warn : h.direction === "start" || h.direction === "therapist" ? COLORS.lav : COLORS.ok }} />
                    <span><b>{h.from ? `${h.from} → ` : ""}{h.to}</b> <span className="muted">· {h.reason}{h.at ? ` · ${new Date(h.at).toLocaleDateString()}` : ""}</span></span>
                  </li>
                ))}
              </ol>
              <h3 className="mt-5 text-sm font-bold">Screening history (profile re-anchoring)</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {data.profile_history.map((h) => (
                  <li key={h.session_id} className="flex justify-between gap-2">
                    <Link className="text-brand hover:underline" to={`/admin/pipeline/${h.session_id}`}>{new Date(h.created_at).toLocaleDateString()}</Link>
                    <span>{FOCUS_LABEL[h.focus]} · <SeverityChip level={h.severity_level} /></span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="This week's schedule (dose from severity)" icon={<CalendarRange size={18} className="text-navy" />}>
              <p className="mb-3 text-xs muted">{plan.dose.sessions_per_week} sessions × {plan.dose.minutes_per_session} min · {plan.dose.exercises_per_session} exercises each</p>
              <div className="grid grid-cols-7 gap-1.5 text-center text-xs">
                {plan.week.map((d) => (
                  <div key={d.date} className={`rounded-lg p-2 ${d.is_today ? "ring-2 ring-navy" : ""} ${d.active ? "bg-lav-50" : "bg-canvas"}`}>
                    <div className="font-bold">{d.day}</div>
                    <div className="muted">{d.active ? `${d.minutes}m` : "rest"}</div>
                    <div className="mt-1 font-semibold" style={{ color: d.completed ? COLORS.ok : COLORS.muted }}>{d.completed ? `✓ ${d.completed}` : "–"}</div>
                  </div>
                ))}
              </div>
            </Card>
          </section>

          <Card title="Attempts">
            {data.attempts.length === 0 ? <p className="text-sm muted">No exercises completed yet.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide muted">
                    <th className="py-2">When</th><th>Exercise</th><th>Score</th><th>Voice active</th><th>Long pauses</th><th>wpm / target</th><th>Goal</th><th>Felt</th>
                  </tr></thead>
                  <tbody className="divide-y divide-line">
                    {data.attempts.map((a, i) => (
                      <tr key={i}>
                        <td className="py-1.5 text-xs muted">{new Date(a.completed_at).toLocaleString()}</td>
                        <td className="font-semibold">{a.title}</td>
                        <td className="font-mono font-bold">{a.score}</td>
                        <td className="font-mono">{a.speaking_ratio !== null ? `${(a.speaking_ratio * 100).toFixed(0)}%` : "–"}</td>
                        <td className="font-mono">{a.speaking_ratio !== null ? a.long_pauses : "–"}</td>
                        <td className="font-mono">{a.measured_wpm ? `${a.measured_wpm} / ${a.target_wpm}` : "–"}</td>
                        <td className="font-mono">{a.items_total ? `${a.items_clear}/${a.items_total}` : a.max_phonation_sec ? `${a.max_phonation_sec}s` : "–"}</td>
                        <td>{a.self_rating}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title="AI assistant conversations" icon={<Bot size={18} className="text-navy" />}>
            {data.assistant_log.length === 0 ? <p className="text-sm muted">No questions asked yet.</p> : (
              <ul className="space-y-3">
                {data.assistant_log.map((m, i) => (
                  <li key={i} className="rounded-xl border border-line p-3 text-sm">
                    <div className="flex flex-wrap justify-between gap-2 text-xs muted">
                      <span>{new Date(m.created_at).toLocaleString()}</span>
                      <span>route <b className="text-ink">{m.source}</b> · intent {m.intent ?? "–"} ({(m.confidence * 100).toFixed(0)}%)</span>
                    </div>
                    <p className="mt-1 font-semibold text-ink">Q: {m.question}</p>
                    <p className="mt-1 text-ink-soft">A: {m.reply}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
