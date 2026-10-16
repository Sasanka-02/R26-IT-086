"""
SpeakFree integration layer - connects the four components inside the Component 1 host app.

    C1  speech screening (this backend)      ->  session summary + per-recording JSON
    C2  speakfree-component2/backend/component2  articulation score (novelty) + fluency events
    C3  speakfree-component3/backend/component3  model-based severity classification (novelty)
    C4  speakfree-component4/backend/component4  adaptive therapy plans + AI assistant (novelty)

Each component lives in its own folder as a plain Python package. This module puts their
`backend/` folders on sys.path so the host can import them (no extra servers, no HTTP hops).
Set SPEAKFREE_ROOT to point at a different checkout.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(os.getenv("SPEAKFREE_ROOT", BACKEND_DIR.parents[1])).resolve()
COMPONENT_DIRS = {n: ROOT / f"speakfree-component{n}" / "backend" for n in (2, 3, 4)}

for _path in COMPONENT_DIRS.values():
    if _path.is_dir() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
