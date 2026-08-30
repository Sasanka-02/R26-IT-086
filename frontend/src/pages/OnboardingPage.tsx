import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Sparkles, User, ShieldCheck, AlertCircle } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { useIntake } from "../context/IntakeContext";
import { AgeCategory } from "../types";
import { DisorderType, DISORDER_TYPE_LABELS } from "../types/intake";

const DISORDER_OPTIONS: DisorderType[] = ["none", "stuttering", "dysarthria", "articulation"];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { setAgeCategory } = useSession();
  const { saveIntake } = useIntake();

  const [nickname, setNickname] = useState("");
  const [ageCategory, setLocalAgeCategory] = useState<AgeCategory | null>(null);
  const [disorderType, setDisorderType] = useState<DisorderType | null>(null);
  const [previousTherapyNotes, setPreviousTherapyNotes] = useState("");
  const [consents, setConsents] = useState({
    regulatoryCompliance: false,
    audioStoragePolicy: false,
    participationConsent: false,
  });
  const [showValidation, setShowValidation] = useState(false);

  const allConsentsGiven =
    consents.regulatoryCompliance && consents.audioStoragePolicy && consents.participationConsent;
  const isValid = nickname.trim().length > 0 && ageCategory !== null && allConsentsGiven;

  const toggleConsent = (key: keyof typeof consents) => {
    setConsents((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!isValid || !ageCategory) {
      setShowValidation(true);
      return;
    }

    saveIntake({
      nickname: nickname.trim(),
      ageCategory,
      disorderType,
      previousTherapyNotes: previousTherapyNotes.trim(),
      consents,
      completedAt: new Date().toISOString(),
    });
    setAgeCategory(ageCategory);
    navigate("/screening");
  };

  return (
    <div className="min-h-screen bg-paper px-6 py-10">
      <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-8">
        <header className="text-center">
          <div className="flex items-center justify-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-600 text-white">
              <Mic size={16} />
            </div>
            <span className="font-display text-lg font-semibold text-ink">SpeakFree</span>
          </div>
          <h1 className="mt-4 font-display text-2xl font-semibold text-ink">
            Patient Intake &amp; Consent Form
          </h1>
          <p className="mt-1 text-sm text-ink-soft">
            Parents/guardians, please help complete this profile before we start.
          </p>
        </header>

        {/* Section 1 — Patient Profile */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6">
          <div className="flex items-center gap-2 border-b border-teal-100 pb-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-teal-100 text-xs font-semibold text-teal-700">
              1
            </span>
            <h2 className="font-display font-semibold text-ink">Patient Profile</h2>
          </div>

          <div className="mt-4 space-y-5">
            <div>
              <label className="text-sm font-medium text-ink">
                Name or nickname <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="e.g. Alex"
                className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              {showValidation && nickname.trim().length === 0 && (
                <p className="mt-1 flex items-center gap-1 text-xs text-red-600">
                  <AlertCircle size={12} /> Please enter a name or nickname.
                </p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium text-ink">
                Age category <span className="text-red-500">*</span>
              </label>
              <div className="mt-2 grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setLocalAgeCategory("kids")}
                  className={`flex items-center gap-3 rounded-xl border-2 p-4 text-left transition ${
                    ageCategory === "kids"
                      ? "border-gold-500 bg-gold-400/10"
                      : "border-teal-100 bg-white hover:border-teal-300"
                  }`}
                >
                  <Sparkles className="text-gold-600" size={20} />
                  <div>
                    <p className="text-sm font-semibold text-ink">Child / Junior (4–12)</p>
                    <p className="text-xs text-ink-soft">Fun, game-like prompts</p>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setLocalAgeCategory("adults")}
                  className={`flex items-center gap-3 rounded-xl border-2 p-4 text-left transition ${
                    ageCategory === "adults"
                      ? "border-teal-500 bg-teal-50"
                      : "border-teal-100 bg-white hover:border-teal-300"
                  }`}
                >
                  <User className="text-teal-600" size={20} />
                  <div>
                    <p className="text-sm font-semibold text-ink">Adult / Teen (13+)</p>
                    <p className="text-xs text-ink-soft">Standard clinical screening</p>
                  </div>
                </button>
              </div>
              {showValidation && ageCategory === null && (
                <p className="mt-1 flex items-center gap-1 text-xs text-red-600">
                  <AlertCircle size={12} /> Please choose an age category.
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Section 2 — Clinical History */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6">
          <div className="flex items-center gap-2 border-b border-teal-100 pb-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-teal-100 text-xs font-semibold text-teal-700">
              2
            </span>
            <h2 className="font-display font-semibold text-ink">Clinical History</h2>
            <span className="ml-auto text-xs text-ink-soft">Optional</span>
          </div>

          <div className="mt-4 space-y-5">
            <div>
              <label className="text-sm font-medium text-ink">Known disorder type</label>
              <div className="mt-2 flex flex-wrap gap-2">
                {DISORDER_OPTIONS.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => setDisorderType(opt)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                      disorderType === opt
                        ? "border-teal-600 bg-teal-600 text-white"
                        : "border-teal-100 bg-white text-ink-soft hover:border-teal-300"
                    }`}
                  >
                    {DISORDER_TYPE_LABELS[opt]}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-ink">
                Previous therapy experience
              </label>
              <textarea
                value={previousTherapyNotes}
                onChange={(e) => setPreviousTherapyNotes(e.target.value)}
                rows={3}
                placeholder="Has the patient had speech therapy before? Are there specific sounds they struggle with?"
                className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>
          </div>
        </section>

        {/* Section 3 — Privacy & Consents */}
        <section className="rounded-2xl border border-teal-100 bg-white p-6">
          <div className="flex items-center gap-2 border-b border-teal-100 pb-3">
            <ShieldCheck className="text-teal-600" size={18} />
            <h2 className="font-display font-semibold text-ink">Privacy &amp; Consents</h2>
            <span className="ml-auto text-xs font-medium text-red-500">Mandatory</span>
          </div>

          <div className="mt-4 space-y-3">
            <ConsentRow
              checked={consents.regulatoryCompliance}
              onToggle={() => toggleConsent("regulatoryCompliance")}
              label="Regulatory compliance"
              description="I acknowledge that this platform adheres to PDPA guidelines for data protection and medical privacy."
            />
            <ConsentRow
              checked={consents.audioStoragePolicy}
              onToggle={() => toggleConsent("audioStoragePolicy")}
              label="Audio storage policy"
              description="I understand that session data is anonymized and no raw audio recordings are permanently stored on SpeakFree servers."
            />
            <ConsentRow
              checked={consents.participationConsent}
              onToggle={() => toggleConsent("participationConsent")}
              label="Participation consent"
              description="I consent to participate in this clinical screening and understand I retain the right to withdraw at any time."
            />
          </div>

          {showValidation && !allConsentsGiven && (
            <p className="mt-3 flex items-center gap-1 text-xs text-red-600">
              <AlertCircle size={12} /> All three consents are required to continue.
            </p>
          )}
        </section>

        <button
          type="submit"
          className="w-full rounded-full bg-teal-600 px-6 py-3 text-sm font-semibold text-white hover:bg-teal-700"
        >
          Continue to Screening
        </button>
      </form>
    </div>
  );
}

function ConsentRow({
  checked,
  onToggle,
  label,
  description,
}: {
  checked: boolean;
  onToggle: () => void;
  label: string;
  description: string;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-teal-100 p-3 hover:bg-teal-50/50">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="mt-0.5 h-4 w-4 rounded border-teal-300 text-teal-600 focus:ring-teal-500"
      />
      <div>
        <p className="text-sm font-medium text-ink">{label}</p>
        <p className="text-xs text-ink-soft">{description}</p>
      </div>
    </label>
  );
}