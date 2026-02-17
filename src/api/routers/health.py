"""Health check and public info endpoints"""

import os

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

_LEGAL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "legal")


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    # TODO: Check DB, Redis, Ollama connections
    return {"status": "ready"}


@router.get("/privacy", response_class=PlainTextResponse)
async def privacy_policy():
    """Serve the privacy policy (RGPD Art. 13/14 transparency)."""
    path = os.path.normpath(os.path.join(_LEGAL_DIR, "privacy-policy.md"))
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return "Privacy policy not available."
