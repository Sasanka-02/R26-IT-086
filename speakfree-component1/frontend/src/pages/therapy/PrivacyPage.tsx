/**
 * PrivacyPage – what SpeakFree stores about the active patient, what it never stores, how the clinic's
 * shared statistics are protected (differential privacy budget) and a download of the patient's own data.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Bot, Database, Download, EyeOff, Loader2, Lock, ShieldCheck } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { Bar, Card, COLORS, ErrorBox, Spinner } from "../../components/ui";
import type { PrivacyInfo } from "../../types/integration";

export default function PrivacyPage() {
  const { activePatient } = useAuth();
  const [info, setInfo] = useState<PrivacyInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!activePatient) return;
    api.therapy.privacy(activePatient.id).then(setInfo).catch((e: Error) => setError(e.message));
  }, [activePatient]);

  async function download() {
    if (!activePatient) return;
    setDownloading(true);
    try {
      const data = await api.therapy.exportData(activePatient.id);
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `speakfree-therapy-${activePatient.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  }

  if (!activePatient) return <div className="card p-8 text-center muted">No patient selected.</div>;
  if (error && !info) return <ErrorBox message={error} />;
  if (!info) return <Spinner />;
  const dp = info.cohort_privacy;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link to="/therapy-plan" className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted hover:text-ink"><ArrowLeft size={14} /> My therapy plan</Link>
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Privacy & my data</h1>
        <p className="mt-1 text-sm text-ink-soft">{activePatient.full_name} · what is saved, what never leaves this device, and how shared statistics are protected.</p>
      </div>
      <ErrorBox message={error} />

      <div className="grid gap-5 md:grid-cols-2">
        <Card title="What SpeakFree saves" icon={<Database size={18} className="text-navy" />}>
          <ul className="space-y-3">
            {info.stored.map((s) => (
              <li key={s.label} className="flex gap-3 text-sm">
                <span className="grid h-9 min-w-[2.25rem] shrink-0 place-items-center rounded-xl bg-lav-100 font-bold text-navy">{s.count}</span>
                <span><b className="text-ink">{s.label}</b><span className="block text-xs muted">{s.detail}</span></span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="What is never saved" icon={<EyeOff size={18} className="text-navy" />}>
          <ul className="space-y-3">
            {info.never_stored.map((s) => <li key={s} className="flex gap-2.5 text-sm text-ink"><Lock size={16} className="mt-0.5 shrink-0 text-ok" />{s}</li>)}
          </ul>
          <p className="mt-4 flex gap-2.5 rounded-xl bg-canvas p-3 text-xs text-ink-soft"><Bot size={16} className="shrink-0 text-lav-600" />{info.assistant_ai}</p>
        </Card>
      </div>

      <Card title="Shared statistics are protected" icon={<ShieldCheck size={18} className="text-navy" />}>
        <p className="text-sm text-ink-soft">{dp.explanation}</p>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs font-semibold text-ink-soft">
            <span>Privacy budget used by the clinic</span><span className="font-mono text-ink">ε {dp.epsilon_spent} of {dp.epsilon_threshold}</span>
          </div>
          <Bar value={(dp.epsilon_spent / dp.epsilon_threshold) * 100} color={dp.exhausted ? COLORS.bad : COLORS.lav} className="h-2.5" />
          <p className="mt-2 text-xs muted">
            {dp.exhausted ? "The budget is used up – no more shared statistics can be released." : `ε ${dp.epsilon_remaining} left. Your own dashboard and your therapist always see exact numbers – noise is only added to statistics that leave the clinic.`}
          </p>
        </div>
      </Card>

      <section className="card flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
        <Download className="shrink-0 text-navy" />
        <p className="flex-1 text-sm text-ink-soft"><b className="text-ink">Download my therapy data.</b> A JSON file with your practice results, homework, notes from your therapist and assistant questions.</p>
        <button className="btn-primary" disabled={downloading} onClick={() => void download()}>{downloading ? <Loader2 className="animate-spin" size={16} /> : <Download size={16} />} Download</button>
      </section>
    </div>
  );
}
