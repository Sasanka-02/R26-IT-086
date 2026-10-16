"""Sends Component 2's articulation result to Component 3 over HTTP."""
import logging
import os

import requests

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10


def component3_url() -> str:
    return os.getenv("SPEAKFREE_COMPONENT3_URL", "").strip()


def send_to_component3(payload: dict) -> dict:
    """POST the payload as JSON. Never raises: the delivery outcome is returned instead."""
    url = component3_url()
    if not url:
        return {"status": "not_configured",
                "message": "Set SPEAKFREE_COMPONENT3_URL to Component 3's endpoint to send results."}
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Sending to Component 3 at %s failed: %s", url, exc)
        return {"status": "failed", "url": url, "error": str(exc)}
    return {"status": "sent", "url": url, "http_status": response.status_code}
