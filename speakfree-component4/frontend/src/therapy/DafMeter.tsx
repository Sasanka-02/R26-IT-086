import { Volume2 } from "lucide-react";

/** Live microphone level and playback volume for the DAF screens, so the
 *  student can see that the app hears them and turn the playback up. */
export default function DafMeter({
  active,
  level,
  heardVoice,
  calibrating = false,
  volume,
  onVolume,
}: {
  active: boolean;
  level: number;
  heardVoice: boolean;
  calibrating?: boolean;
  volume: number;
  onVolume: (value: number) => void;
}) {
  return (
    <div className="space-y-3 rounded-xl border border-teal-100 bg-paper p-4">
      <div>
        <div className="mb-1 flex items-center justify-between text-xs font-medium text-ink-soft">
          <span>Microphone level</span>
          <span>
            {!active
              ? "Off"
              : calibrating
              ? "Get ready — stay quiet a moment…"
              : heardVoice
              ? "We can hear you ✓"
              : "Start speaking…"}
          </span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-snow/[0.08]" aria-hidden="true">
          <div
            className="h-full rounded-full bg-teal-600 transition-[width] duration-100"
            style={{ width: `${Math.round(level * 100)}%` }}
          />
        </div>
      </div>
      <label className="block">
        <span className="flex items-center gap-1.5 text-xs font-medium text-ink-soft">
          <Volume2 size={13} /> Playback volume: {volume}×
        </span>
        <input
          type="range"
          min={1}
          max={8}
          step={1}
          value={volume}
          onChange={(e) => onVolume(Number(e.target.value))}
          className="mt-1 w-full accent-teal-600"
        />
      </label>
      {active && heardVoice && (
        <p className="text-xs text-ink-soft">
          The bar moves but you hear nothing? Check that your headphones are the selected sound output on your
          computer and that the computer's volume is up.
        </p>
      )}
      {active && !heardVoice && !calibrating && (
        <p className="text-xs text-gold-600">
          If the level bar doesn't move when you speak, check the microphone selected for this site (the mic icon in
          the address bar) and that your headphones' microphone isn't muted.
        </p>
      )}
    </div>
  );
}
