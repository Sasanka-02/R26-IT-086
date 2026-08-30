import { useEffect, useState } from "react";
import { Volume2 } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import AudioVisualizer from "../components/AudioVisualizer";
import RecorderControls from "../components/RecorderControls";
import { CONVERSATION_PROMPTS } from "./conversationPrompts";
import { AgeCategory } from "../types";

interface TaskConversationProps {
  ageCategory: AgeCategory;
  onSubmit: (blob: Blob) => void;
}

export default function TaskConversation({
  ageCategory,
  onSubmit,
}: TaskConversationProps) {
  const prompts = CONVERSATION_PROMPTS[ageCategory];
  const [promptIndex, setPromptIndex] = useState(0);
  const [hasSpoken, setHasSpoken] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recorder = useAudioRecorder();

  const currentPrompt = prompts[promptIndex];

  useEffect(() => {
    setHasSpoken(false);
    setIsSpeaking(false);
    recorder.clearRecording();
    return () => {
      window.speechSynthesis?.cancel();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [promptIndex]);

  const playQuestion = () => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      setHasSpoken(true);
      recorder.startRecording();
      return;
    }

    setIsSpeaking(true);
    const utterance = new SpeechSynthesisUtterance(currentPrompt.text);
    utterance.rate = ageCategory === "kids" ? 0.9 : 1.0;
    utterance.onend = () => {
      setIsSpeaking(false);
      setHasSpoken(true);
      recorder.startRecording();
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      setHasSpoken(true);
    };

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const handleSubmit = () => {
    if (recorder.audioBlob) onSubmit(recorder.audioBlob);
  };

  const handleNextPrompt = () => {
    if (promptIndex < prompts.length - 1) setPromptIndex((i) => i + 1);
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Task 3 — Conversation
        </h2>
        <p className="text-sm text-slate-600">
          Tap the button to hear the question, then answer naturally when
          you're ready.
        </p>
      </div>

      <div className="rounded-lg border border-brand-100 bg-brand-50 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-brand-600">
          Question {promptIndex + 1} of {prompts.length}
        </p>
        <p className="mt-1 text-slate-800">{currentPrompt.text}</p>

        {!hasSpoken && (
          <button
            type="button"
            onClick={playQuestion}
            disabled={isSpeaking}
            className="mt-3 flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Volume2 size={16} />
            {isSpeaking ? "Speaking..." : "Play Question"}
          </button>
        )}
      </div>

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
        disabled={!hasSpoken}
        onStart={recorder.startRecording}
        onStop={recorder.stopRecording}
        onPause={recorder.pauseRecording}
        onResume={recorder.resumeRecording}
        onReset={recorder.clearRecording}
      />

      {recorder.audioUrl && (
        <div className="flex flex-wrap gap-3">
          <audio controls src={recorder.audioUrl} className="w-full" />
          {promptIndex < prompts.length - 1 ? (
            <button
              type="button"
              onClick={handleNextPrompt}
              className="rounded-lg bg-slate-200 px-4 py-2 font-medium text-slate-800 hover:bg-slate-300"
            >
              Next Question
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              className="rounded-lg bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700"
            >
              Finish &amp; Submit
            </button>
          )}
        </div>
      )}
    </div>
  );
}