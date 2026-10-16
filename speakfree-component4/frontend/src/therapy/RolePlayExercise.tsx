import { useState } from "react";
import { Eye, EyeOff, Lightbulb, MessageSquare } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";
import RecordingPlayer from "../components/RecordingPlayer";
import { TherapyExercise } from "../types/therapy";
import CompletionPanel from "./CompletionPanel";

/**
 * A real-life situation answered out loud: class presentations, ordering
 * food, phone calls, job interviews. The situation and the other person's
 * lines are on screen; the student records their answers.
 */
export default function RolePlayExercise({ exercise }: { exercise: TherapyExercise }) {
  const recorder = useAudioRecorder();
  const [showExamples, setShowExamples] = useState(false);

  return (
    <div className="space-y-4 rounded-2xl border border-teal-100 bg-white p-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{exercise.title}</h2>
        <p className="mt-2 rounded-xl border border-teal-100 bg-teal-50/60 px-4 py-3 text-base text-ink">
          <span className="mr-1 font-semibold">Situation:</span>
          {exercise.description}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <p className="mb-2 flex items-center gap-2 text-sm font-medium text-ink">
            <MessageSquare size={16} className="text-teal-600" />
            Answer each line out loud, one at a time
          </p>
          <ol className="space-y-2">
            {exercise.prompts.map((line, i) => {
              const [who, ...rest] = line.split(": ");
              const speaker = rest.length ? who : null;
              const text = rest.length ? rest.join(": ") : line;
              return (
                <li key={line} className="flex gap-3">
                  <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-600 text-xs font-semibold text-white">
                    {i + 1}
                  </span>
                  <div className="rounded-2xl rounded-tl-sm border border-teal-100 bg-paper px-4 py-2.5 text-base text-ink">
                    {speaker && <span className="block text-xs font-semibold text-teal-700">{speaker}</span>}
                    {text}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>

        {exercise.example_sentences.length > 0 && (
          <aside className="rounded-xl border border-gold-400/60 bg-gold-400/10 p-4 lg:col-span-2" aria-label="Example answers">
            <div className="flex items-center justify-between gap-2">
              <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                <Lightbulb size={16} className="text-gold-600" />
                Example answers
              </p>
              <button
                type="button"
                onClick={() => setShowExamples((v) => !v)}
                className="flex items-center gap-1 rounded-full border border-gold-500/50 bg-white px-2.5 py-0.5 text-xs font-medium text-gold-600"
              >
                {showExamples ? <EyeOff size={12} /> : <Eye size={12} />}
                {showExamples ? "Hide" : "Show"}
              </button>
            </div>
            {showExamples ? (
              <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-ink">
                {exercise.example_sentences.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            ) : (
              <p className="mt-2 text-xs text-ink-soft">Try your own words first. Peek if you get stuck.</p>
            )}
          </aside>
        )}
      </div>

      <AudioVisualizer analyserNode={recorder.analyserNode} isRecording={recorder.isRecording} />

      {recorder.isRecording && recorder.calibrating && (
        <p className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-800" role="status">
          Get ready — stay quiet for a moment while we listen to the room…
        </p>
      )}
      {recorder.permissionError && <p className="text-sm text-red-600">{recorder.permissionError}</p>}

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
          <RecordingPlayer src={recorder.audioUrl} label="Listen to your answers" />
          {recorder.heardSpeech ? (
            <CompletionPanel
              key={recorder.audioUrl}
              metrics={{ exercise_id: exercise.id, duration_seconds: recorder.recordingTime }}
            />
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-ink" role="alert">
              <p className="font-medium">We didn't hear your answers, so this hasn't been scored.</p>
              <p className="mt-1 text-ink-soft">
                A score needs at least 2 seconds of your voice. Press Start Recording, wait for “Get ready”, then
                answer the lines out loud.
              </p>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-ink-soft">
        Tip: take a calm breath before each answer, start softly, and pause between ideas — just like a real
        conversation. The recording stays on this device.
      </p>
    </div>
  );
}
