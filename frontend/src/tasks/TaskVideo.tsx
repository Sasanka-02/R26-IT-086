import { useState } from "react";
import { VideoOff } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";

interface TaskVideoProps {
  videoSrc: string;
  onSubmit: (blob: Blob) => void;
}

export default function TaskVideo({ videoSrc, onSubmit }: TaskVideoProps) {
  const recorder = useAudioRecorder();
  const [videoEnded, setVideoEnded] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);

  const handleSubmit = () => {
    if (recorder.audioBlob) onSubmit(recorder.audioBlob);
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Task 2 — Video Description
        </h2>
        <p className="text-sm text-slate-600">
          Watch the short clip below. Once it finishes, describe what
          happened in your own words — recording controls unlock
          automatically.
        </p>
      </div>

      {videoFailed ? (
        <div className="flex h-56 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 text-slate-400">
          <VideoOff size={32} />
          <p className="text-xs">
            Add a video at <code>public{videoSrc}</code>
          </p>
          <button
            type="button"
            onClick={() => setVideoEnded(true)}
            className="mt-1 text-xs font-medium text-brand-600 underline"
          >
            Skip for now (dev only)
          </button>
        </div>
      ) : (
        <video
          src={videoSrc}
          controls
          muted
          className="w-full rounded-lg border border-slate-200 bg-black"
          onEnded={() => setVideoEnded(true)}
          onError={() => setVideoFailed(true)}
        />
      )}

      {!videoEnded && !videoFailed && (
        <p className="text-sm text-slate-500">
          Recording will be available once the video finishes playing.
        </p>
      )}

      {videoEnded && (
        <>
          <AudioVisualizer
            analyserNode={recorder.analyserNode}
            isRecording={recorder.isRecording}
          />

          {recorder.permissionError && (
            <p className="text-sm text-red-600">{recorder.permissionError}</p>
          )}

          <RecorderControls
            isRecording={recorder.isRecording}
            isPaused={recorder.isPaused}
            hasRecording={!!recorder.audioBlob}
            onStart={recorder.startRecording}
            onStop={recorder.stopRecording}
            onPause={recorder.pauseRecording}
            onResume={recorder.resumeRecording}
            onReset={recorder.clearRecording}
          />

          {recorder.audioUrl && (
            <div className="space-y-3">
              <audio controls src={recorder.audioUrl} className="w-full" />
              <button
                type="button"
                onClick={handleSubmit}
                className="rounded-lg bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700"
              >
                Continue
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}