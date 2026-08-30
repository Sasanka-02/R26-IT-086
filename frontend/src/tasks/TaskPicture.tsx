import { useState } from "react";
import { ImageOff } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";

interface TaskPictureProps {
  imageSrc: string;
  onSubmit: (blob: Blob) => void;
}

export default function TaskPicture({ imageSrc, onSubmit }: TaskPictureProps) {
  const recorder = useAudioRecorder();
  const [imageFailed, setImageFailed] = useState(false);

  const handleSubmit = () => {
    if (recorder.audioBlob) onSubmit(recorder.audioBlob);
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Task 1 — Picture Description
        </h2>
        <p className="text-sm text-slate-600">
          Take your time and describe what you see in the image below, in
          your own words. There is no time limit.
        </p>
      </div>

      {imageFailed ? (
        <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 text-slate-400">
          <ImageOff size={32} />
          <p className="text-xs">
            Add an image at <code>public{imageSrc}</code>
          </p>
        </div>
      ) : (
        <img
          src={imageSrc}
          alt="Describe what is happening in this picture"
          className="max-h-80 w-full rounded-lg border border-slate-200 object-contain bg-white"
          onError={() => setImageFailed(true)}
        />
      )}

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
    </div>
  );
}