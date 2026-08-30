import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import TaskPicture from "../tasks/TaskPicture";
import TaskVideo from "../tasks/TaskVideo";
import TaskConversation from "../tasks/TaskConversation";
import LoadingIndicator from "../components/LoadingIndicator";
import ResultsPanel from "../components/ResultsPanel";
import { extractFeatures } from "../services/api";
import { useSession } from "../context/SessionContext";
import { ExtractFeaturesResponse, TaskType } from "../types";

type Stage = "picture" | "video" | "conversation" | "done";
const STAGE_ORDER: Stage[] = ["picture", "video", "conversation", "done"];

export default function ScreeningWorkflow() {
  const navigate = useNavigate();
  const { sessionId, ageCategory } = useSession();
  const [stage, setStage] = useState<Stage>("picture");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Partial<Record<TaskType, ExtractFeaturesResponse>>>({});

  useEffect(() => {
    if (!ageCategory) navigate("/start");
  }, [ageCategory, navigate]);

  if (!ageCategory) return null;

  const isKid = ageCategory === "kids";
  const advanceStage = () => {
    const i = STAGE_ORDER.indexOf(stage);
    setStage(STAGE_ORDER[i + 1] ?? "done");
  };

  const handleTaskSubmit = async (taskType: TaskType, blob: Blob) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await extractFeatures({
        audioBlob: blob,
        taskType,
        sessionId,
        ageCategory,
      });
      setResults((prev) => ({ ...prev, [taskType]: result }));
      advanceStage();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while processing your recording. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const stageIndex = STAGE_ORDER.indexOf(stage);

  return (
    <div
      className={
        isKid
          ? "min-h-screen bg-gradient-to-b from-gold-400/10 via-teal-100/40 to-paper"
          : "min-h-screen bg-paper"
      }
    >
      <div className="mx-auto max-w-2xl space-y-6 p-6">
        <header className="space-y-3">
          <h1 className="font-display text-2xl font-semibold text-ink">
            {isKid ? "SpeakFree — Let's Play!" : "SpeakFree — Speech Screening"}
          </h1>

          {isKid ? (
            <div className="flex items-center gap-2">
              {STAGE_ORDER.slice(0, 3).map((s, i) => (
                <Star
                  key={s}
                  size={22}
                  className={
                    i <= stageIndex
                      ? "fill-gold-500 text-gold-500"
                      : "text-teal-100"
                  }
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-ink-soft">
              Step {Math.min(stageIndex + 1, 3)} of 3
            </p>
          )}
        </header>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {isSubmitting && (
          <LoadingIndicator
            message={
              isKid
                ? "Magic brain is thinking... 🧠✨"
                : "Analyzing fluency and speech features..."
            }
          />
        )}

        {!isSubmitting && stage === "picture" && (
          <TaskPicture
            imageSrc="/stimuli/images/picture-1.jpg"
            onSubmit={(blob) => handleTaskSubmit("picture_description", blob)}
          />
        )}

        {!isSubmitting && stage === "video" && (
          <TaskVideo
            videoSrc="/stimuli/videos/clip-1.mp4"
            onSubmit={(blob) => handleTaskSubmit("video_description", blob)}
          />
        )}

        {!isSubmitting && stage === "conversation" && (
          <TaskConversation
            ageCategory={ageCategory}
            onSubmit={(blob) => handleTaskSubmit("conversation", blob)}
          />
        )}

        {stage === "done" && (
          <div className="space-y-6">
            <div className="rounded-2xl border border-teal-100 bg-teal-50 px-6 py-8 text-center">
              <p className="text-2xl">{isKid ? "🎉🏆🎉" : "✓"}</p>
              <h2 className="mt-2 font-display text-xl font-semibold text-teal-800">
                {isKid ? "Mission Accomplished!" : "Screening Complete"}
              </h2>
              <p className="mt-1 text-sm text-teal-700">
                All three tasks are done. Results are below.
              </p>
              <button
                onClick={() => navigate("/dashboard")}
                className="mt-4 rounded-full bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
              >
                Back to Dashboard
              </button>
            </div>

            {(Object.keys(results) as TaskType[]).map((taskType) => (
              <div key={taskType} className="space-y-2">
                <h3 className="font-display font-semibold capitalize text-ink">
                  {taskType.replace("_", " ")}
                </h3>
                <ResultsPanel result={results[taskType]!} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}