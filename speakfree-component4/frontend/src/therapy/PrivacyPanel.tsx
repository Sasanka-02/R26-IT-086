import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { getPrivacyBudget, getFederatedArchitecture } from "./therapyApi";
import { PrivacyBudget } from "../types/therapy";
import { usePracticeHistory } from "../context/PracticeHistoryContext";

export default function PrivacyPanel() {
  const { userId } = usePracticeHistory();
  const [budget, setBudget] = useState<PrivacyBudget | null>(null);
  const [architecture, setArchitecture] = useState<Record<string, unknown> | null>(null);

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
          <li>Never saved or uploaded: your voice recordings.</li>
          <li>Your results are stored only under your own account. Your therapist can see them; other students cannot.</li>
          <li>Any statistics shared outside the clinic include differential-privacy noise, so no single attempt can be identified.</li>
        </ul>
      </div>

      {architecture && (
        <div className="rounded-xl bg-paper p-4 text-xs text-ink-soft">
          <p className="font-medium text-ink">
            Federated learning architecture (design, not live in this demo)
          </p>
          <p className="mt-1">
            {String(architecture.protocol)} via {String(architecture.framework)} — raw
            audio never leaves the device.
          </p>
        </div>
      )}
    </div>
  );
}
