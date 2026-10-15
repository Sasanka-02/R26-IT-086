# Task images

Images placed here are served at `http://localhost:8000/static/tasks/<file>` and shown on the
Picture / Scenario task pages instead of the emoji illustration.

## Naming

Name the file after the task id, with one of these extensions:

```
<task_id>.png    <task_id>.jpg    <task_id>.jpeg    <task_id>.webp
```

Examples: `b1-pic-1.png` (Bracket 1 "Flying a Kite"), `b3-scn-2.jpg`.
Task ids are listed in the clinician **Task Library** page, or in `backend/task_bank.py`.

## Linking an image to a task

- **Seeded tasks:** add the file here, then run `python seed.py` again. Tasks that have no image
  yet get their `image_path` filled in; nothing else is changed.
- **Any task:** a clinician can upload or replace an image in the **Task Library** page
  (jpg / png / webp, max 5 MB). The upload is saved here as `<task_id>.<ext>`.

Use original or properly licensed pictures only, and avoid identifiable real children.
Landscape images around 1200 × 800 px work best.
