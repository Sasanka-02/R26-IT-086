"""
Age-based task delivery from the assessment_tasks table.

For each task type the patient's bracket is filtered to ACTIVE tasks, then the tasks this
patient has attempted least often (task_attempts) are kept and one is chosen at random
(three for pre-defined questions). Untried tasks therefore always come first, so a patient
who repeats the screening rotates through the library.

The random generator is seeded with (patient id, number of attempts): repeated GETs return
the same set until the patient actually attempts something, so a page reload in the middle
of a session never swaps the tasks the patient is recording.
"""
from __future__ import annotations

import random
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import AssessmentTask, TaskAttempt

QUESTIONS_PER_SESSION = 3
SINGLE_TYPES = ("reading", "picture", "scenario")


class TaskLibraryEmpty(Exception):
    """Raised when a bracket has no active task of a required type (run `python seed.py`)."""


def attempt_counts(db: Session, patient_id: str) -> Counter:
    rows = db.execute(
        select(TaskAttempt.task_id, func.count()).where(TaskAttempt.patient_id == patient_id).group_by(TaskAttempt.task_id)
    ).all()
    return Counter({task_id: n for task_id, n in rows})


def least_attempted(tasks: list[AssessmentTask], counts: Counter, k: int, rng: random.Random) -> list[AssessmentTask]:
    """Pick k tasks, fewest attempts first; ties are broken randomly."""
    shuffled = list(tasks)
    rng.shuffle(shuffled)
    return sorted(shuffled, key=lambda t: counts.get(t.id, 0))[:k]


def pick_tasks(db: Session, patient_id: str, bracket: int, rng: random.Random | None = None) -> dict[str, list[AssessmentTask]]:
    counts = attempt_counts(db, patient_id)
    rng = rng or random.Random(f"{patient_id}:{sum(counts.values())}")
    active = db.scalars(
        select(AssessmentTask)
        .where(AssessmentTask.age_bracket == bracket, AssessmentTask.is_active.is_(True))
        .order_by(AssessmentTask.id)
    ).all()
    by_type: dict[str, list[AssessmentTask]] = {}
    for t in active:
        by_type.setdefault(t.task_type, []).append(t)

    picked: dict[str, list[AssessmentTask]] = {}
    for task_type in SINGLE_TYPES:
        if not by_type.get(task_type):
            raise TaskLibraryEmpty(task_type)
        picked[task_type] = least_attempted(by_type[task_type], counts, 1, rng)
    if not by_type.get("questions"):
        raise TaskLibraryEmpty("questions")
    # questions are shown in a stable order (by id) once the least-attempted ones are chosen
    picked["questions"] = sorted(least_attempted(by_type["questions"], counts, QUESTIONS_PER_SESSION, rng), key=lambda t: t.id)
    return picked


# --------------------------------------------------------------------------- serialisation
def image_url(task: AssessmentTask, base_url: str) -> str | None:
    if not task.image_path:
        return None
    return f"{base_url.rstrip('/')}/static/{task.image_path.lstrip('/')}"


def task_payload(task: AssessmentTask, base_url: str) -> dict:
    """Shape the frontend already uses (task_bank format), plus image_url."""
    base = {"id": task.id, "title": task.title, "instructions": task.instructions, "max_seconds": task.max_seconds}
    if task.task_type == "reading":
        return {**base, "text": task.content_text}
    if task.task_type == "picture":
        visual = task.visual_json or {"kind": "emoji", "emojis": ["🖼️"], "caption": task.content_text}
        return {**base, "visual": visual, "image_url": image_url(task, base_url), "keywords": list(task.keywords or [])}
    if task.task_type == "scenario":
        return {**base, "prompt": task.content_text, "visual": task.visual_json, "image_url": image_url(task, base_url)}
    return {"id": task.id, "prompt": task.content_text, "max_seconds": task.max_seconds}  # one question item


def task_set_payload(picked: dict[str, list[AssessmentTask]], base_url: str) -> dict:
    questions = picked["questions"]
    return {
        "reading": task_payload(picked["reading"][0], base_url),
        "picture": task_payload(picked["picture"][0], base_url),
        "scenario": task_payload(picked["scenario"][0], base_url),
        "questions": {
            "id": f"b{questions[0].age_bracket}-qs",
            "title": "Pre-defined Questions",
            "instructions": questions[0].instructions,
            "items": [task_payload(q, base_url) for q in questions],
        },
    }
