/**
 * TaskLibrary – clinician-only management of the assessment task database.
 *   • browse tasks by age bracket and type (inactive ones included, greyed out)
 *   • add a task, edit it, upload / replace / remove its picture, activate or deactivate it
 * Backend: GET/POST/PATCH /api/v1/admin/tasks (multipart, image ≤ 5 MB, jpg/png/webp).
 */
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import { BookOpen, ImagePlus, Library, Loader2, MessagesSquare, Pencil, Plus, Power, Trash2, X } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import TaskVideo from "../components/TaskVideo";
import { ErrorBox, SceneVisual, Spinner } from "../components/ui";
import { TASK_LABEL, type AdminTask, type TaskType } from "../types";
import { SCREENING_BRACKETS as BRACKETS } from "../utils/age";

const TYPES: TaskType[] = ["picture", "scenario", "questions", "reading"];
const MAX_IMAGE_MB = 5;
const MAX_VIDEO_MB = 25; // short scenario videos (backend MAX_VIDEO_MB)
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
const VIDEO_TYPES = ["video/mp4", "video/webm"];

const CONTENT_LABEL: Record<TaskType, string> = {
  reading: "Reading passage",
  picture: "Picture caption (also the alt text)",
  scenario: "Scenario prompt",
  questions: "Question",
};

// =========================================================================== editor
function TaskEditor({ task, bracket, onClose, onSaved }: {
  task: AdminTask | null; // null = create
  bracket: number;
  onClose: () => void;
  onSaved: (t: AdminTask) => void;
}) {
  const [ageBracket, setAgeBracket] = useState(task?.age_bracket ?? bracket);
  const [taskType, setTaskType] = useState<TaskType>(task?.task_type ?? "picture");
  const [title, setTitle] = useState(task?.title ?? "");
  const [instructions, setInstructions] = useState(task?.instructions ?? "");
  const [content, setContent] = useState(task?.content_text ?? "");
  const [keywords, setKeywords] = useState((task?.keywords ?? []).join(", "));
  const [maxSeconds, setMaxSeconds] = useState(task?.max_seconds ?? 60);
  const [isActive, setIsActive] = useState(task?.is_active ?? true);
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(task?.video_url ?? task?.image_url ?? null);
  const [previewIsVideo, setPreviewIsVideo] = useState(!!task?.video_url);
  const [removeImage, setRemoveImage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const hasImage = taskType === "picture" || taskType === "scenario";
  const allowVideo = taskType === "scenario";

  useEffect(() => () => { if (image && preview) URL.revokeObjectURL(preview); }, [image, preview]);

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const video = VIDEO_TYPES.includes(f.type);
    if (video && !allowVideo) return setError("Videos can only be used for scenario tasks.");
    if (!video && !IMAGE_TYPES.includes(f.type)) return setError(allowVideo ? "Use a JPG, PNG or WebP picture, or an MP4 / WebM video." : "Image must be a JPG, PNG or WebP file.");
    const maxMb = video ? MAX_VIDEO_MB : MAX_IMAGE_MB;
    if (f.size > maxMb * 1024 * 1024) return setError(`${video ? "Video" : "Image"} must be ${maxMb} MB or smaller.`);
    setError(null);
    setImage(f);
    setRemoveImage(false);
    setPreviewIsVideo(video);
    setPreview(URL.createObjectURL(f));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const form = new FormData();
    if (!task) {
      form.append("age_bracket", String(ageBracket));
      form.append("task_type", taskType);
    }
    form.append("title", title.trim());
    form.append("instructions", instructions.trim());
    form.append("content_text", content.trim());
    form.append("max_seconds", String(maxSeconds));
    form.append("keywords", taskType === "picture" ? keywords : "");
    form.append("is_active", String(isActive));
    if (task && removeImage && !image) form.append("remove_image", "true");
    if (image && hasImage) form.append("image", image, image.name);
    setBusy(true);
    try {
      onSaved(task ? await api.adminTasks.update(task.id, form) : await api.adminTasks.create(form));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-ink/40 p-4" role="dialog" aria-modal>
      <form onSubmit={submit} className="card my-8 w-full max-w-2xl space-y-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">{task ? `Edit ${task.id}` : "Add a task"}</h2>
          <button type="button" onClick={onClose} className="text-ink-muted" aria-label="Close"><X size={18} /></button>
        </div>
        <ErrorBox message={error} />

        <div className="grid gap-4 sm:grid-cols-3">
          <label className="block"><span className="label">Age bracket</span>
            <select className="input" value={ageBracket} disabled={!!task} onChange={(e) => setAgeBracket(Number(e.target.value))}>
              {BRACKETS.map((b) => <option key={b.id} value={b.id}>{b.id} · {b.label}</option>)}
            </select>
          </label>
          <label className="block"><span className="label">Task type</span>
            <select className="input" value={taskType} disabled={!!task} onChange={(e) => setTaskType(e.target.value as TaskType)}>
              {TYPES.map((t) => <option key={t} value={t}>{TASK_LABEL[t]}</option>)}
            </select>
          </label>
          <label className="block"><span className="label">Max seconds</span>
            <input className="input" type="number" min={10} max={300} value={maxSeconds} onChange={(e) => setMaxSeconds(Number(e.target.value))} required />
          </label>
        </div>

        <label className="block"><span className="label">Title</span>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required minLength={2} maxLength={200} />
        </label>
        <label className="block"><span className="label">Instructions shown to the patient</span>
          <input className="input" value={instructions} onChange={(e) => setInstructions(e.target.value)} required minLength={2} />
        </label>
        <label className="block"><span className="label">{CONTENT_LABEL[taskType]}</span>
          <textarea className="input min-h-[96px]" value={content} onChange={(e) => setContent(e.target.value)} required minLength={2} />
        </label>
        {taskType === "picture" && (
          <label className="block"><span className="label">Keywords for content coverage (comma separated)</span>
            <input className="input" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="kite, girl, park, wind" />
          </label>
        )}

        {hasImage && (
          <div className="rounded-xl border border-line bg-canvas/60 p-4">
            <div className="mb-2 text-sm font-semibold text-ink-soft">
              {allowVideo
                ? `Picture (JPG, PNG or WebP, max ${MAX_IMAGE_MB} MB) or short video (MP4 or WebM, max ${MAX_VIDEO_MB} MB)`
                : `Picture (JPG, PNG or WebP, max ${MAX_IMAGE_MB} MB)`}
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="h-28 w-44 shrink-0 overflow-hidden rounded-lg border border-line bg-white">
                {preview && !removeImage
                  ? (previewIsVideo
                    ? <video src={preview} controls muted playsInline preload="metadata" className="h-full w-full bg-ink object-contain" />
                    : <img src={preview} alt="Task" className="h-full w-full object-cover" />)
                  : <div className="grid h-full place-items-center text-xs muted">No picture – emoji illustration is used</div>}
              </div>
              <div className="flex flex-wrap gap-2">
                <label className="btn-lav cursor-pointer"><ImagePlus size={15} /> {preview && !removeImage ? "Replace" : "Upload"} {allowVideo ? "picture / video" : "picture"}
                  <input type="file" className="hidden" onChange={onPick}
                    accept={allowVideo ? ".png,.jpg,.jpeg,.webp,.mp4,.webm,image/png,image/jpeg,image/webp,video/mp4,video/webm" : ".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"} />
                </label>
                {preview && !removeImage && (
                  <button type="button" className="btn-ghost py-2" onClick={() => { setImage(null); setPreview(null); setRemoveImage(true); }}>
                    <Trash2 size={15} /> Remove
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-[#1E3A8A]" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active – can be given to patients
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={busy}>{busy && <Loader2 className="animate-spin" size={16} />} {task ? "Save changes" : "Add task"}</button>
        </div>
      </form>
    </div>
  );
}

// =========================================================================== card
function TaskCard({ task, onEdit, onToggle, busy }: { task: AdminTask; onEdit: () => void; onToggle: () => void; busy: boolean }) {
  const visual = task.task_type === "picture" || task.task_type === "scenario";
  return (
    <article className={`card flex flex-col p-4 transition ${task.is_active ? "" : "opacity-60"}`}>
      {visual ? (
        task.video_url
          ? <TaskVideo preview src={task.video_url} title={task.title} className="h-36" />
          : <SceneVisual visual={task.visual_json} imageUrl={task.image_url} alt={task.content_text} tone={task.task_type === "picture" ? "park" : "indoor"} className="h-36" />
      ) : (
        <div className="flex h-36 items-start gap-2 overflow-hidden rounded-xl border border-line bg-lav-50 p-3 text-sm text-ink-soft">
          {task.task_type === "questions" ? <MessagesSquare size={16} className="mt-0.5 shrink-0 text-lav-500" /> : <BookOpen size={16} className="mt-0.5 shrink-0 text-lav-500" />}
          <p className="line-clamp-5">{task.content_text}</p>
        </div>
      )}
      <div className="mt-3 flex items-center gap-2">
        <span className="chip bg-lav-100 font-mono text-lav-600">{task.id}</span>
        <span className={`chip ${task.is_active ? "bg-ok-soft text-ok" : "bg-canvas text-ink-muted"}`}>{task.is_active ? "Active" : "Inactive"}</span>
      </div>
      <h3 className="mt-2 font-bold leading-snug">{task.title}</h3>
      <p className="mt-0.5 line-clamp-2 text-xs text-ink-soft">{task.instructions}</p>
      <div className="mt-2 flex flex-wrap gap-x-3 text-[11px] muted">
        <span>{TASK_LABEL[task.task_type]}</span>
        <span>{task.max_seconds}s</span>
        <span>{task.attempt_count} attempt{task.attempt_count === 1 ? "" : "s"}</span>
        {task.image_path && <span>{task.video_url ? "has video" : "has picture"}</span>}
      </div>
      <div className="mt-auto flex gap-2 pt-4">
        <button className="btn-outline flex-1 py-2" onClick={onEdit}><Pencil size={14} /> Edit</button>
        <button className="btn-ghost py-2" onClick={onToggle} disabled={busy} title={task.is_active ? "Deactivate" : "Activate"}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Power size={14} />} {task.is_active ? "Deactivate" : "Activate"}
        </button>
      </div>
    </article>
  );
}

// =========================================================================== page
export default function TaskLibrary() {
  const { user } = useAuth();
  const [bracket, setBracket] = useState(1);
  const [type, setType] = useState<TaskType | "all">("all");
  const [tasks, setTasks] = useState<AdminTask[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AdminTask | "new" | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);

  const load = useCallback(() => {
    setTasks(null);
    setError(null);
    api.adminTasks.list({ ageBracket: bracket }).then(setTasks).catch((e: Error) => setError(e.message));
  }, [bracket]);
  const canManage = user?.role === "clinician" || user?.role === "admin";
  useEffect(() => { if (canManage) load(); }, [load, canManage]);

  const shown = useMemo(() => (tasks ?? []).filter((t) => type === "all" || t.task_type === type), [tasks, type]);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const t of tasks ?? []) if (t.is_active) c[t.task_type] = (c[t.task_type] ?? 0) + 1;
    return c;
  }, [tasks]);

  if (!canManage) {
    return <div className="card p-8 text-center"><h1 className="text-xl font-bold">Task Library</h1><p className="mt-2 muted">Only clinician accounts can manage the task library.</p></div>;
  }

  async function toggle(task: AdminTask) {
    const form = new FormData();
    form.append("is_active", String(!task.is_active));
    setToggling(task.id);
    try {
      const updated = await api.adminTasks.update(task.id, form);
      setTasks((ts) => ts?.map((t) => (t.id === updated.id ? updated : t)) ?? null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setToggling(null);
    }
  }

  function onSaved(saved: AdminTask) {
    setEditing(null);
    if (saved.age_bracket !== bracket) {
      setBracket(saved.age_bracket);
      return;
    }
    setTasks((ts) => {
      const list = ts ?? [];
      return list.some((t) => t.id === saved.id) ? list.map((t) => (t.id === saved.id ? saved : t)) : [...list, saved];
    });
  }

  const b = BRACKETS.find((x) => x.id === bracket)!;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight"><Library size={26} className="text-navy" /> Task Library</h1>
          <p className="mt-1 text-sm text-ink-soft">Tasks are given to each patient by age bracket; patients get tasks they have not tried yet first.</p>
        </div>
        <button className="btn-primary" onClick={() => setEditing("new")}><Plus size={16} /> Add task</button>
      </div>

      <div className="card space-y-3 p-4">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Age bracket">
          {BRACKETS.map((x) => (
            <button key={x.id} role="tab" aria-selected={x.id === bracket} onClick={() => setBracket(x.id)}
              className={`rounded-xl border px-3 py-2 text-sm font-semibold transition ${x.id === bracket ? "border-navy bg-navy text-white" : "border-line bg-white text-ink-soft hover:bg-canvas"}`}>
              Bracket {x.id} <span className="font-normal opacity-80">· {x.label.replace("Ages ", "")}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-ink-muted">Type:</span>
          {(["all", ...TYPES] as const).map((t) => (
            <button key={t} onClick={() => setType(t)}
              className={`chip ${t === type ? "bg-lav-100 text-lav-600" : "bg-canvas text-ink-muted hover:text-ink"}`}>
              {t === "all" ? "All" : TASK_LABEL[t]}{t !== "all" && ` (${counts[t] ?? 0})`}
            </button>
          ))}
        </div>
        <p className="text-xs muted">{b.focus}</p>
      </div>

      <ErrorBox message={error} />
      {!tasks ? <Spinner /> : shown.length === 0 ? (
        <div className="card p-8 text-center muted">No tasks of this type in bracket {bracket}.</div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {shown.map((t) => <TaskCard key={t.id} task={t} busy={toggling === t.id} onEdit={() => setEditing(t)} onToggle={() => void toggle(t)} />)}
        </div>
      )}

      {editing && (
        <TaskEditor task={editing === "new" ? null : editing} bracket={bracket} onClose={() => setEditing(null)} onSaved={onSaved} />
      )}
    </div>
  );
}
