import { useState } from "react";
import { ImageOff, MessageCircleQuestion } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";
import { TherapyExercise } from "../types/therapy";
import CompletionPanel from "./CompletionPanel";

interface PictureDescriptionExerciseProps {
  exercise: TherapyExercise;
}

export default function PictureDescriptionExercise({
  exercise,
}: PictureDescriptionExerciseProps) {
  const recorder = useAudioRecorder();
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="text-sm text-ink-soft">{exercise.description}</p>
      </div>

      {exercise.image_url && !imageFailed ? (
        <img
          src={exercise.image_url}
          alt="Describe what is happening in this picture"
          className="max-h-80 w-full rounded-xl border border-teal-100 object-contain bg-paper"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-teal-200 bg-paper text-ink-soft">
          <ImageOff size={32} />
          <p className="text-xs">
            Add an image at <code>public{exercise.image_url ?? "/stimuli/images/picture-1.jpg"}</code>
          </p>
        </div>
      )}

      {exercise.prompts.length > 0 && (
        <div className="rounded-xl bg-paper p-4">
          <p className="flex items-center gap-2 text-sm font-medium text-ink">
            <MessageCircleQuestion size={16} className="text-teal-600" />
            Questions to help you
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-6 text-sm text-ink-soft">
            {exercise.prompts.map((prompt) => (
              <li key={prompt}>{prompt}</li>
            ))}
          </ul>
        </div>
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
          <CompletionPanel
            key={recorder.audioUrl}
            metrics={{ exercise_id: exercise.id, duration_seconds: recorder.recordingTime }}
          />
        </div>
      )}

      <p className="text-xs text-ink-soft">
        Privacy: this recording stays in your browser for review only — it
        isn't uploaded or stored anywhere.
      </p>
    </div>
  );
}