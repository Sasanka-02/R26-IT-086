import { useState } from "react";
import { ImageOff, CheckCircle2 } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";
import { TherapyExercise } from "../types/therapy";
import { usePracticeHistory } from "../context/PracticeHistoryContext";

interface PictureDescriptionExerciseProps {
  exercise: TherapyExercise;
}

export default function PictureDescriptionExercise({
  exercise,
}: PictureDescriptionExerciseProps) {
  const recorder = useAudioRecorder();
  const { recordCompletion } = usePracticeHistory();
  const [imageFailed, setImageFailed] = useState(false);
  const [markedDone, setMarkedDone] = useState(false);

  const handleMarkDone = () => {
    recordCompletion(exercise);
    setMarkedDone(true);
  };

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

      {recorder.audioUrl && !markedDone && (
        <div className="space-y-3">
          <audio controls src={recorder.audioUrl} className="w-full" />
          <button
            type="button"
            onClick={handleMarkDone}
            className="flex items-center gap-2 rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700"
          >
            <CheckCircle2 size={16} />
            Mark Complete
          </button>
        </div>
      )}

      {markedDone && (
        <div className="flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
          <CheckCircle2 size={18} />
          Nice work — this exercise is complete.
        </div>
      )}

      <p className="text-xs text-ink-soft">
        Privacy: this recording stays in your browser for review only — it
        isn't uploaded or stored anywhere.
      </p>
    </div>
  );
}