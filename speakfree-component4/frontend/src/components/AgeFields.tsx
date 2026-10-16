import { AGE_GROUP_INFO, AgeGroup } from "../types/therapy";

export const MIN_AGE = 6;
export const MAX_AGE = 100;
export const GUARDIAN_UNDER = 18;

/** Same rule as the backend's age_group_for: 6–13 child, 14–20 teen, 21+ adult. */
export function ageGroupFor(age: number): AgeGroup | null {
  if (!Number.isFinite(age) || age < MIN_AGE || age > MAX_AGE) return null;
  if (age <= 13) return "child";
  if (age <= 20) return "teen";
  return "adult";
}

/** Error message for an age, or null when it is acceptable (guardian checked separately). */
export function ageError(raw: string): string | null {
  if (raw.trim() === "") return "Please enter your age.";
  const age = Number(raw);
  if (!Number.isInteger(age)) return "Please enter your age as a whole number.";
  if (age < MIN_AGE) return "This app is for ages 6 and above.";
  if (age > MAX_AGE) return `Please enter an age between ${MIN_AGE} and ${MAX_AGE}.`;
  return null;
}

/** Age input with the practice group it leads to, plus the guardian agreement under 18. */
export default function AgeFields({
  age,
  onAge,
  guardian,
  onGuardian,
}: {
  age: string;
  onAge: (value: string) => void;
  guardian: boolean;
  onGuardian: (value: boolean) => void;
}) {
  const value = Number(age);
  const error = age.trim() === "" ? null : ageError(age);
  const group = error ? null : ageGroupFor(value);
  return (
    <div className="space-y-3">
      <div>
        <label className="text-sm font-medium text-ink-soft" htmlFor="age">
          Age
        </label>
        <input
          id="age"
          type="number"
          inputMode="numeric"
          required
          min={MIN_AGE}
          max={MAX_AGE}
          value={age}
          onChange={(e) => onAge(e.target.value)}
          className="mt-1 w-full rounded-lg border border-teal-100 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          placeholder="e.g. 12"
        />
        {error && (
          <p className="mt-1 text-xs font-medium text-red-700" role="alert">
            {error}
          </p>
        )}
        {group && (
          <p className="mt-1 text-xs text-teal-700">
            You'll get <strong>{AGE_GROUP_INFO[group].label}</strong> ({AGE_GROUP_INFO[group].ages}) — exercises made
            for your age.
          </p>
        )}
      </div>
      {group && value < GUARDIAN_UNDER && (
        <label className="flex items-start gap-2 rounded-lg border border-gold-400/50 bg-gold-400/10 p-3 text-xs text-ink">
          <input
            type="checkbox"
            required
            checked={guardian}
            onChange={(e) => onGuardian(e.target.checked)}
            className="mt-0.5 accent-teal-600"
          />
          <span>A parent or guardian has agreed to this account.</span>
        </label>
      )}
    </div>
  );
}
