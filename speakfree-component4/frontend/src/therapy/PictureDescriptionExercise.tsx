import { useState } from "react";
import { Eye, EyeOff, ImageOff, Lightbulb, MessageCircleQuestion } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";
import { TherapyExercise } from "../types/therapy";
import CompletionPanel from "./CompletionPanel";
import RecordingPlayer from "../components/RecordingPlayer";

interface PictureDescriptionExerciseProps {
  exercise: TherapyExercise;
}

export default function PictureDescriptionExercise({
  exercise,
}: PictureDescriptionExerciseProps) {
  const recorder = useAudioRecorder();
  const [imageFailed, setImageFailed] = useState(false);
  const [showExamples, setShowExamples] = useState(true);

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="text-sm text-ink-soft">{exercise.description}</p>
      </div>

      {/* Picture on the left, example sentences beside it on the right (stacked on phones). */}
      <div
        className={`grid gap-4 ${
          exercise.example_sentences.length > 0 && showExamples ? "lg:grid-cols-5" : ""
        }`}
      >
        <div className={exercise.example_sentences.length > 0 && showExamples ? "lg:col-span-3" : ""}>
          {exercise.image_url && !imageFailed ? (
            <img
              src={exercise.image_url}
              alt="Describe what is happening in this picture"
              className="h-full max-h-[26rem] w-full rounded-xl border border-teal-100 bg-paper object-contain"
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
        </div>

        {exercise.example_sentences.length > 0 && showExamples && (
          <aside
            className="flex flex-col rounded-xl border border-gold-400/60 bg-gold-400/10 p-4 lg:col-span-2"
            aria-label="Example sentences"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Lightbulb size={16} className="shrink-0 text-gold-600" />
                Example sentences
              </p>
              <button
                type="button"
                onClick={() => setShowExamples(false)}
                className="flex shrink-0 items-center gap-1 rounded-full border border-gold-500/50 bg-white px-2.5 py-0.5 text-xs font-medium text-gold-600 hover:bg-gold-400/10"
              >
                <EyeOff size={12} />
                Hide
              </button>
            </div>
            <ol className="mt-3 list-decimal space-y-2 pl-6 text-base leading-relaxed text-ink">
              {exercise.example_sentences.map((sentence) => (
                <li key={sentence}>{sentence}</li>
              ))}
            </ol>
            <p className="mt-auto pt-3 text-xs text-ink-soft">
              Read them aloud slowly, one sentence at a time, pausing between them. Then try adding one detail
              of your own.
            </p>
          </aside>
        )}
      </div>

      {exercise.example_sentences.length > 0 && !showExamples && (
        <button
          type="button"
          onClick={() => setShowExamples(true)}
          className="flex items-center gap-1.5 rounded-full border border-gold-500/50 bg-gold-400/10 px-3 py-1 text-sm font-medium text-gold-600 hover:bg-gold-400/20"
        >
          <Eye size={14} />
          Show example sentences
        </button>
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

      {recorder.isRecording && recorder.calibrating && (
        <p className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-800" role="status">
          Get ready — stay quiet for a moment while we listen to the room…
        </p>
      )}

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
          <RecordingPlayer src={recorder.audioUrl} label="Listen to your description" />
          {recorder.heardSpeech ? (
            <CompletionPanel
              key={recorder.audioUrl}
              metrics={{ exercise_id: exercise.id, duration_seconds: recorder.recordingTime }}
              recordingUrl={recorder.audioUrl}
            />
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
              <p className="font-medium">We didn't hear you describing the picture, so this hasn't been scored.</p>
              <p className="mt-1 text-ink-soft">
                A score needs at least 2 seconds of your voice. Press Start Recording, wait for “Get ready” to
                finish, then describe the picture aloud. Play the recording above to check what was picked up.
              </p>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-ink-soft">
        Privacy: after you save, this recording is shared with your therapist so they can listen and give
        feedback. You can switch this off on the Privacy tab.
      </p>
    </div>
  );
}