"""Health check endpoints"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    # TODO: Check DB, Redis, Ollama connections
    return {"status": "ready"}
