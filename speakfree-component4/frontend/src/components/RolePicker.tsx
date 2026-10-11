import { GraduationCap, Stethoscope } from "lucide-react";
import { UserRole } from "../context/AuthContext";

const OPTIONS: { value: UserRole; label: string; hint: string; icon: typeof GraduationCap }[] = [
  { value: "student", label: "Student", hint: "Practise exercises", icon: GraduationCap },
  { value: "therapist", label: "Therapist", hint: "Review students", icon: Stethoscope },
];

export default function RolePicker({
  value,
  onChange,
}: {
  value: UserRole;
  onChange: (role: UserRole) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-ink-soft">I am a</p>
      <div className="mt-1 grid grid-cols-2 gap-2" role="radiogroup">
        {OPTIONS.map(({ value: v, label, hint, icon: Icon }) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={value === v}
            onClick={() => onChange(v)}
            className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-left transition ${
              value === v
                ? "border-teal-600 bg-teal-50 text-teal-800"
                : "border-teal-100 text-ink-soft hover:border-teal-400"
            }`}
          >
            <Icon size={18} className={value === v ? "text-teal-600" : ""} />
            <span>
              <span className="block text-sm font-semibold">{label}</span>
              <span className="block text-xs opacity-80">{hint}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
