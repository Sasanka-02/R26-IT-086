"""
Low-latency WebSocket streaming contract for Component 4 (real-time therapy / DAF)
=================================================================================

Producer (browser, Component 4 UI):   ws://<host>/ws/therapy/{session_id}?token=<JWT>
  -> send TEXT  {"type":"config","sample_rate":16000,"encoding":"pcm_s16le"}   (optional, once)
  -> send BINARY  raw PCM16 little-endian mono chunks, <= 300 ms each (<= 4800 samples @16 kHz)
  -> send TEXT  {"type":"ping","client_ts":<ms>}   (optional, for round-trip latency)
  <- receives TEXT {"type":"chunk_ack", seq, chunk_ms, processing_ms, rms_db, zcr, voiced, within_budget}

Consumer (Component 4 service):       ws://<host>/ws/therapy/{session_id}/listen?token=<JWT>
  <- receives TEXT {"type":"chunk_meta", seq, ...metrics} followed by BINARY (the same PCM chunk)

Delayed Auditory Feedback itself runs in the browser (Web Audio DelayNode) so that the
audible delay never depends on network latency; the server only forwards and measures.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict

import numpy as np
from fastapi import WebSocket


def chunk_metrics(pcm: np.ndarray, sample_rate: int) -> dict:
    """Very cheap per-chunk features (< 1 ms for 300 ms of audio)."""
    if pcm.size == 0:
        return {"chunk_ms": 0.0, "rms_db": -100.0, "zcr": 0.0, "voiced": False}
    x = pcm.astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(x ** 2) + 1e-12))
    rms_db = 20 * np.log10(max(rms, 1e-10))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(x).astype(np.int8))))) if x.size > 1 else 0.0
    return {
        "chunk_ms": round(pcm.size / sample_rate * 1000, 1),
        "rms_db": round(rms_db, 2),
        "zcr": round(zcr, 4),
        "voiced": bool(rms_db > -45 and zcr < 0.35),
    }


class TherapyStreamHub:
    """Fan-out of producer chunks to any Component 4 listeners in the same session."""

    def __init__(self) -> None:
        self._listeners: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def add_listener(self, session_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._listeners[session_id].add(ws)

    async def remove_listener(self, session_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._listeners[session_id].discard(ws)
            if not self._listeners[session_id]:
                self._listeners.pop(session_id, None)

    def listener_count(self, session_id: str) -> int:
        return len(self._listeners.get(session_id, ()))

    async def forward(self, session_id: str, meta: dict, chunk: bytes) -> None:
        dead = []
        for ws in list(self._listeners.get(session_id, ())):
            try:
                await ws.send_json({"type": "chunk_meta", **meta})
                await ws.send_bytes(chunk)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.remove_listener(session_id, ws)


hub = TherapyStreamHub()
