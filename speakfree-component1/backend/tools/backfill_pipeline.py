"""
Run the integrated pipeline (C2 → C3 → C4) for finalised screening sessions that don't have a
pipeline run yet – e.g. screenings made before the integration. Safe to run again.

    cd backend
    python tools/backfill_pipeline.py            # only sessions without a run
    python tools/backfill_pipeline.py --all      # re-run every session
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from database import PipelineRun, ScreeningSession, SessionLocal, run_migrations  # noqa: E402
from integration.pipeline import run_session_pipeline  # noqa: E402


def main(rerun_all: bool = False) -> None:
    run_migrations()
    with SessionLocal() as db:
        done = set(db.scalars(select(PipelineRun.session_id)).all())
        sessions = db.scalars(select(ScreeningSession).order_by(ScreeningSession.created_at)).all()
        todo = [s.id for s in sessions if rerun_all or s.id not in done]
        print(f"{len(sessions)} screening sessions, {len(todo)} to process")
        for sid in todo:
            run = run_session_pipeline(db, sid)
            print(f"  {sid[:8]}…  {run.status:9s}  C2={run.articulation_score}  C3={run.primary_disorder} L{run.severity_level}"
                  f"  C4={run.therapy_focus}  {run.error or ''}")


if __name__ == "__main__":
    main("--all" in sys.argv)
