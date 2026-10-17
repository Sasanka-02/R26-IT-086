import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, ShieldCheck, Trash2 } from "lucide-react";
import {
  deleteMyAccount,
  downloadMyData,
  getFederatedArchitecture,
  getPrivacyBudget,
  setRecordingSharing,
} from "./therapyApi";
import { useAuth } from "../context/AuthContext";
import { PrivacyBudget } from "../types/therapy";
import { usePracticeHistory } from "../context/PracticeHistoryContext";

export default function PrivacyPanel() {
  const { userId } = usePracticeHistory();
  const [budget, setBudget] = useState<PrivacyBudget | null>(null);
  const [architecture, setArchitecture] = useState<Record<string, unknown> | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const { logout, user, updateUser } = useAuth();
  const sharing = user?.share_recordings !== false;

  const toggleSharing = async () => {
    try {
      updateUser(await setRecordingSharing(!sharing));
    } catch {
      setDataError("Couldn't change the recording setting. Try again.");
    }
  };
  const navigate = useNavigate();

  const removeAccount = async () => {
    try {
      await deleteMyAccount();
      logout();
      navigate("/");
    } catch {
      setDataError("Couldn't delete your account. Try again.");
    }
  };

  useEffect(() => {
    getPrivacyBudget(userId).then(setBudget);
    getFederatedArchitecture().then(setArchitecture);
  }, [userId]);

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div className="flex items-center gap-2">
        <ShieldCheck className="text-teal-600" size={18} />
        <h3 className="font-display font-semibold text-ink">Privacy</h3>
      </div>

      {budget && (
        <div>
          <p className="text-sm text-ink-soft">
            Clinic privacy budget used for shared cohort reports:{" "}
            <strong className="text-ink">
              {budget.epsilon_spent} / {budget.epsilon_threshold} ε
            </strong>
          </p>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-teal-50">
            <div
              className="h-full bg-teal-600"
              style={{
                width: `${Math.min(100, (budget.epsilon_spent / budget.epsilon_threshold) * 100)}%`,
              }}
            />
          </div>
          {budget.inference_only && (
            <p className="mt-1 text-xs text-gold-600">
              Budget exhausted — this account is now inference-only.
            </p>
          )}
        </div>
      )}

      <div className="rounded-xl bg-paper p-4 text-sm text-ink-soft">
        <p className="font-medium text-ink">What is saved for {userId}</p>
        <ul className="mt-1 list-disc space-y-1 pl-5">
          <li>Saved: exercise name, date, practice time, score, number of long pauses, and your “how did it feel” rating.</li>
          <li>
            Your practice recordings: shared with your therapist so they can listen and give feedback
            {user?.share_recordings === false ? " — currently switched off." : "."}
          </li>
          <li>Your results and recordings are stored only under your own account. Your therapist can see and hear them; other students cannot.</li>
          <li>Any statistics shared outside the clinic include differential-privacy noise, so no single attempt can be identified.</li>
        </ul>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-100 p-4 text-sm">
        <div className="max-w-xl">
          <p className="font-medium text-ink">Share my recordings with my therapist</p>
          <p className="mt-0.5 text-xs text-ink-soft">
            When on, each saved exercise's recording goes to your therapist so they can listen, rate it and help you.
            When off, recordings stay on your device and only your scores are saved.
          </p>
        </div>
        <button
          role="switch"
          aria-checked={sharing}
          onClick={toggleSharing}
          className={`relative h-7 w-12 shrink-0 rounded-full transition ${sharing ? "bg-teal-600" : "bg-snow/20"}`}
        >
          <span className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${sharing ? "left-6" : "left-1"}`} />
          <span className="sr-only">{sharing ? "On" : "Off"}</span>
        </button>
      </div>

      <div className="rounded-xl border border-teal-100 p-4 text-sm">
        <p className="font-medium text-ink">Your data, your choice</p>
        <p className="mt-1 text-xs text-ink-soft">
          Under Sri Lanka's Personal Data Protection Act No. 9 of 2022 you can see everything stored about you and
          ask for it to be erased.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => downloadMyData().catch(() => setDataError("Couldn't download your data. Try again."))}
            className="flex items-center gap-1.5 rounded-full border border-teal-200 px-4 py-1.5 text-sm font-medium text-teal-700 hover:bg-teal-50"
          >
            <Download size={14} />
            Download my data
          </button>
          {!confirming ? (
            <button
              onClick={() => setConfirming(true)}
              className="flex items-center gap-1.5 rounded-full border border-red-200 px-4 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
            >
              <Trash2 size={14} />
              Delete my account
            </button>
          ) : (
            <span className="flex flex-wrap items-center gap-2 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">
              This permanently deletes your account and every result. It can't be undone.
              <button
                onClick={removeAccount}
                className="rounded-full bg-red-600 px-3 py-1 font-semibold text-white"
              >
                Yes, delete everything
              </button>
              <button onClick={() => setConfirming(false)} className="rounded-full px-3 py-1 font-medium text-ink">
                Cancel
              </button>
            </span>
          )}
        </div>
        {dataError && <p className="mt-2 text-xs text-red-700">{dataError}</p>}
      </div>

      {architecture && (
        <div className="rounded-xl bg-paper p-4 text-xs text-ink-soft">
          <p className="font-medium text-ink">
            Federated learning — future work (design only, not running)
          </p>
          <p className="mt-1">
            {String(architecture.protocol)} via {String(architecture.framework)} — a design in
            which model training would happen on each device.
          </p>
        </div>
      )}
    </div>
  );
}
