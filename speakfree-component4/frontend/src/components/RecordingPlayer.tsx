import { useEffect, useRef } from "react";

/**
 * Plays back a browser recording. Recordings made with MediaRecorder carry no
 * length, so the browser reports the duration as Infinity: the progress bar
 * and seeking break and playback can appear to stop after the start. Seeking
 * far past the end once makes the browser scan the file and find the real
 * length; then the position is put back to the start.
 */
export default function RecordingPlayer({ src, label }: { src: string; label: string }) {
  const ref = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = ref.current;
    if (!audio) return;
    const fixDuration = () => {
      if (audio.duration !== Infinity && !Number.isNaN(audio.duration)) return;
      const reset = () => {
        audio.removeEventListener("timeupdate", reset);
        audio.currentTime = 0;
      };
      audio.addEventListener("timeupdate", reset);
      audio.currentTime = 1e101;
    };
    audio.addEventListener("loadedmetadata", fixDuration);
    if (audio.readyState >= 1) fixDuration();
    return () => audio.removeEventListener("loadedmetadata", fixDuration);
  }, [src]);

  return (
    <div className="rounded-xl bg-paper p-4">
      <p className="mb-2 text-sm font-medium text-ink">{label}</p>
      <audio ref={ref} controls preload="metadata" src={src} className="w-full" />
    </div>
  );
}
