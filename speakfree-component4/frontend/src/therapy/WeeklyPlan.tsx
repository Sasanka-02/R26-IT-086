import { useEffect, useState } from "react";
import { ListChecks } from "lucide-react";
import { getWeeklyPlan } from "./therapyApi";
import { PlanExercise } from "../types/therapy";

export default function WeeklyPlan({ sessionId }: { sessionId: string }) {
  const [exercises, setExercises] = useState<PlanExercise[]>([]);

  useEffect(() => {
    getWeeklyPlan(sessionId).then(setExercises);
  }, [sessionId]);

  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-6">
      <div className="flex items-center gap-2">
        <ListChecks className="text-teal-600" size={18} />
        <h3 className="font-display font-semibold text-ink">This Week's Plan</h3>
      </div>
      <p className="mt-1 text-xs text-ink-soft">
        Selected by the adaptive planning engine based on your recent progress.
      </p>
      <ul className="mt-4 space-y-2">
        {exercises.map((ex) => (
          <li
            key={ex.id}
            className="flex items-center justify-between rounded-xl bg-paper px-4 py-3 text-sm"
          >
            <span className="text-ink">{ex.title}</span>
            <span className="rounded-full bg-teal-100 px-2.5 py-1 text-xs font-medium text-teal-700">
              Level {ex.difficulty}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
