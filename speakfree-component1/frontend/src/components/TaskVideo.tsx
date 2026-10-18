/**
 * TaskVideo – a short scenario video (Component 1 screening).
 * Full mode: the patient watches it with normal controls (no autoplay, plays inline on phones).
 * Preview mode: a silent still frame with a play badge, for task cards and the Task Library.
 * The scenario page pauses it when recording starts, so its sound is never recorded.
 */
import { forwardRef } from "react";
import { PlayCircle } from "lucide-react";

const TaskVideo = forwardRef<HTMLVideoElement, { src: string; title?: string; className?: string; preview?: boolean }>(
  function TaskVideo({ src, title, className = "", preview = false }, ref) {
    if (preview) {
      return (
        <div className={`relative overflow-hidden rounded-xl bg-ink ${className}`}>
          {/* #t=0.5 shows a real frame instead of a black first frame */}
          <video src={`${src}#t=0.5`} muted playsInline preload="metadata" className="h-full w-full object-cover" aria-hidden />
          <span className="absolute inset-0 grid place-items-center bg-ink/20 text-white" aria-label={title ? `Video: ${title}` : "Video"}>
            <PlayCircle size={40} />
          </span>
        </div>
      );
    }
    return (
      <video ref={ref} src={src} controls playsInline preload="metadata" title={title}
        className={`w-full rounded-xl bg-ink object-contain ${className}`}>
        Your browser cannot play this video.
      </video>
    );
  },
);

export default TaskVideo;
