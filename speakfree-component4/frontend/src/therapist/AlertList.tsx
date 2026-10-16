import { useNavigate } from "react-router-dom";
import { AlertTriangle, BookX, CalendarX, MessageCircle, TrendingDown, UserX } from "lucide-react";
import { StudentAlert } from "../types/therapist";

const ICONS: Record<StudentAlert["kind"], typeof AlertTriangle> = {
  message: MessageCircle,
  not_started: UserX,
  inactive: CalendarX,
  score_drop: TrendingDown,
  hard: AlertTriangle,
  homework_overdue: BookX,
};

const TONES: Record<StudentAlert["severity"], string> = {
  high: "border-red-600/40 bg-red-600/10 text-red-700",
  medium: "border-gold-400/50 bg-gold-400/10 text-gold-600",
  info: "border-teal-600/40 bg-teal-600/10 text-teal-600",
};

/** Plain-sentence alerts ("Kasun hasn't practised for 10 days"); each opens the student. */
export default function AlertList({ alerts, linkToStudent = true }: { alerts: StudentAlert[]; linkToStudent?: boolean }) {
  const navigate = useNavigate();
  return (
    <ul className="space-y-2">
      {alerts.map((a, i) => {
        const Icon = ICONS[a.kind] ?? AlertTriangle;
        const body = (
          <>
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${TONES[a.severity]}`}>
              <Icon size={15} />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-medium text-ink">{a.text}</span>
              {a.detail && <span className="block text-xs text-ink-soft">{a.detail}</span>}
            </span>
          </>
        );
        return (
          <li key={`${a.email}-${a.kind}-${i}`}>
            {linkToStudent ? (
              <button
                onClick={() => navigate(`/therapist/students/${encodeURIComponent(a.email)}`)}
                className="flex w-full items-center gap-3 rounded-xl bg-paper px-4 py-2.5 text-left text-sm hover:bg-teal-50/60"
              >
                {body}
              </button>
            ) : (
              <div className="flex items-center gap-3 rounded-xl bg-paper px-4 py-2.5 text-sm">{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
