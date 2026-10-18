"""
Apply the custom screening content (custom_tasks.py) to an EXISTING database, once:

    python tools/apply_custom_tasks.py            # show what would change
    python tools/apply_custom_tasks.py --apply    # write the changes

For each custom task id it replaces the starter title / instructions / text / keywords – but only
if the task still has its original starter text (a task a clinician already edited is skipped, so
nothing written in the Task Library is overwritten). It links media files in static/tasks/ that
are not linked yet and switches off the third starter picture / scenario of each bracket.
Everything can be undone in the Task Library (edit, re-activate).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from custom_tasks import CUSTOM_TASKS, DISABLED_TASKS  # noqa: E402
from database import AssessmentTask, SessionLocal  # noqa: E402
from seed import find_task_image  # noqa: E402
from task_bank import seed_rows  # noqa: E402

FIELDS = ("title", "instructions", "content_text", "keywords")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    args = ap.parse_args()

    starter = {r["id"]: r for r in seed_rows()}
    updated, skipped, linked, disabled = [], [], [], []
    with SessionLocal() as db:
        tasks = {t.id: t for t in db.scalars(select(AssessmentTask)).all()}
        for task_id, custom in CUSTOM_TASKS.items():
            task = tasks.get(task_id)
            if task is None:
                skipped.append(f"{task_id}: not in the database (run python seed.py first)")
                continue
            original = starter[task_id]
            if any(getattr(task, f) != custom.get(f, original[f]) for f in FIELDS):
                if task.title != original["title"] or task.content_text != original["content_text"]:
                    skipped.append(f"{task_id}: edited in the Task Library - left as it is")
                else:
                    for f in FIELDS:
                        if f in custom:
                            setattr(task, f, custom[f])
                    updated.append(f"{task_id}: {custom['title']}")
            media = find_task_image(task_id, task_type=task.task_type)
            if media and not task.image_path:
                task.image_path = media
                linked.append(f"{task_id} -> {media}")
        for task_id in sorted(DISABLED_TASKS):
            task = tasks.get(task_id)
            if task is not None and task.is_active:
                task.is_active = False
                disabled.append(task_id)
        if args.apply:
            db.commit()
        else:
            db.rollback()

    print(f"{'Applied' if args.apply else 'Dry run'}: {len(updated)} texts updated, {len(linked)} media linked, "
          f"{len(disabled)} starter tasks switched off, {len(skipped)} skipped")
    for title, items in (("Updated", updated), ("Media linked", linked), ("Switched off", disabled), ("Skipped", skipped)):
        if items:
            print(f"\n{title}:\n  " + "\n  ".join(items))
    if not args.apply:
        print("\nNothing was written. Run again with --apply.")


if __name__ == "__main__":
    main()
