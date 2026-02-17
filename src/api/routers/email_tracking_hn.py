"""
Email tracking endpoint pour campagne HackerNews
Task: 20260964
"""

from fastapi import APIRouter, Response
from datetime import datetime
import json
import os
from pathlib import Path

router = APIRouter()

TRACKING_LOG_FILE = "/opt/claude-ceo/workspace/croissance/email_opens_tracking_20260964.json"

def load_tracking_data():
    """Charge les données de tracking"""
    if os.path.exists(TRACKING_LOG_FILE):
        with open(TRACKING_LOG_FILE, 'r') as f:
            return json.load(f)
    return {"opens": []}

def save_tracking_data(data):
    """Sauvegarde les données de tracking"""
    with open(TRACKING_LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@router.get("/track/email/{tracking_id}")
async def track_email_open(tracking_id: str):
    """
    Tracking pixel endpoint
    Returns 1x1 transparent pixel
    """

    # Charger données existantes
    data = load_tracking_data()

    # Ajouter ouverture
    open_event = {
        "tracking_id": tracking_id,
        "opened_at": datetime.now().isoformat(),
        "user_agent": "N/A",  # FastAPI request.headers["user-agent"] si disponible
        "ip": "N/A"
    }

    data["opens"].append(open_event)

    # Sauvegarder
    save_tracking_data(data)

    # Retourner pixel transparent 1x1
    pixel = bytes.fromhex(
        '47494638396101000100800000000000ffffff21f9040100000'
        '02c00000000010001000002024401003b'
    )

    return Response(content=pixel, media_type="image/gif")
