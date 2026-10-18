"""
Seed the assessment_tasks table from task_bank.py.

    python seed.py

Idempotent: tasks that already exist (same id) are skipped, so clinician edits are never
overwritten. If a media file backend/static/tasks/<task_id>.(png|jpg|jpeg|webp) – or, for scenario
tasks, <task_id>.(mp4|webm) – exists and the task has no media yet, its image_path is filled in
(also for existing tasks).

New databases get the custom picture / scenario content from custom_tasks.py (text that matches
the uploaded media, and the starter tasks it replaces switched off). For a database that already
exists, run `python tools/apply_custom_tasks.py` once.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from custom_tasks import apply_custom
from database import AssessmentTask, SessionLocal, run_migrations
from task_bank import seed_rows

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".webm")


@dataclass
class SeedReport:
    inserted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    images_linked: list[str] = field(default_factory=list)


def find_task_image(task_id: str, static_dir: str | None = None, task_type: str = "picture") -> str | None:
    """Media path relative to STATIC_DIR (e.g. "tasks/b2-pic-1.png", "tasks/b2-scn-1.mp4") if a file exists."""
    tasks_dir = os.path.join(static_dir or settings.static_dir, "tasks")
    extensions = IMAGE_EXTENSIONS + (VIDEO_EXTENSIONS if task_type == "scenario" else ())
    for ext in extensions:
        if os.path.isfile(os.path.join(tasks_dir, task_id + ext)):
            return f"tasks/{task_id}{ext}"
    return None


def seed(db: Session, static_dir: str | None = None) -> SeedReport:
    report = SeedReport()
    existing = {t.id: t for t in db.scalars(select(AssessmentTask)).all()}
    for row in seed_rows():
        image = find_task_image(row["id"], static_dir, row["task_type"])
        task = existing.get(row["id"])
        if task is None:
            row = apply_custom(row)  # custom media text + active flag for new databases
            db.add(AssessmentTask(**row, image_path=image))
            report.inserted.append(row["id"])
        else:
            report.skipped.append(row["id"])
            if image and not task.image_path:
                task.image_path = image
        if image and (task is None or task.image_path == image):
            report.images_linked.append(row["id"])
    db.commit()
    return report


def main() -> None:
    if settings.auto_migrate:
        run_migrations()
    with SessionLocal() as db:
        report = seed(db)
    print(f"Seeded assessment_tasks: {len(report.inserted)} inserted, {len(report.skipped)} already present, "
          f"{len(report.images_linked)} with an image.")


if __name__ == "__main__":
    main()
