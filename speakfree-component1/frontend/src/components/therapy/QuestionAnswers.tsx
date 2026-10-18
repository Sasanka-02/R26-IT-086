/**
 * QuestionAnswers – the guiding questions of a picture / conversation / role-play task, each with its
 * example answer right underneath, so the learner can look at them while recording.
 * Answers are shown by default; "Hide answers" lets learners try in their own words first.
 */
import { useState } from "react";
import { Eye, EyeOff, Lightbulb } from "lucide-react";
import ListenButton from "../ListenButton";

export default function QuestionAnswers({ questions, answers, playful = false, speaker = false, wpm }: {
  questions: string[]; answers: string[]; playful?: boolean; speaker?: boolean; wpm?: number;
}) {
  const [show, setShow] = useState(true);
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-sm font-bold text-ink"><Lightbulb size={16} className="text-warn" /> Questions & example answers</p>
        {answers.length > 0 && (
          <button type="button" onClick={() => setShow((v) => !v)} className="chip border border-line bg-white text-ink-soft hover:text-ink">
            {show ? <EyeOff size={12} /> : <Eye size={12} />}{show ? "Hide answers" : "Show answers"}
          </button>
        )}
      </div>
      <ol className="space-y-2">
        {questions.map((q, i) => {
          const [who, ...rest] = speaker ? q.split(": ") : [q];
          return (
            <li key={q} className="overflow-hidden rounded-xl border border-line bg-white">
              <div className={`flex gap-2.5 bg-lav-50 px-3 py-2.5 ${playful ? "text-base" : "text-sm"}`}>
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-navy text-xs font-bold text-white">{i + 1}</span>
                <span className="text-ink">
                  {rest.length > 0 && <span className="block text-xs font-bold text-lav-600">{who}</span>}
                  {rest.length > 0 ? rest.join(": ") : q}
                </span>
              </div>
              {show && answers[i] && (
                <div className="flex items-start justify-between gap-3 border-t border-sun/40 bg-sun-soft px-3 py-2.5">
                  <p className={`text-ink ${playful ? "text-base" : "text-sm"}`}><span className="mr-1 text-xs font-bold uppercase tracking-wide text-warn">Example</span>{answers[i]}</p>
                  <ListenButton text={answers[i]} wpm={wpm} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
      {show && answers.length > 0 && <p className="text-xs muted">These are only examples – your own words are just as good.</p>}
    </div>
  );
}
