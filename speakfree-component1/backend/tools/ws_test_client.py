"""
Quick test for the Component 4 streaming contract.
Usage:  python tools/ws_test_client.py <JWT_TOKEN> [session_id]
Sends 10 x 200 ms chunks of a synthetic tone and prints the server acks + round-trip time.
"""
import asyncio
import json
import sys
import time

import numpy as np
import websockets


async def main(token: str, session_id: str) -> None:
    url = f"ws://localhost:8000/ws/therapy/{session_id}?token={token}"
    async with websockets.connect(url) as ws:
        print(await ws.recv())  # ready
        sr = 16000
        t = np.arange(int(0.2 * sr)) / sr
        chunk = (0.3 * np.sin(2 * np.pi * 200 * t) * 32767).astype(np.int16).tobytes()
        for _ in range(10):
            t0 = time.perf_counter()
            await ws.send(chunk)
            ack = json.loads(await ws.recv())
            print(f"seq={ack['seq']} rtt={(time.perf_counter() - t0) * 1000:.1f} ms  rms_db={ack['rms_db']}  voiced={ack['voiced']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python tools/ws_test_client.py <JWT_TOKEN> [session_id]")
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "test-session"))
