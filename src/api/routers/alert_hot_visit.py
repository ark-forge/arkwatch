"""Alert Hot Visit - SMS temps-réel pour visites pages critiques par leads connus"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Paths
LEADS_DATA_DIR = "/opt/claude-ceo/workspace/croissance"
ALERTS_LOG = "/opt/claude-ceo/workspace/arkwatch/data/hot_visit_alerts.jsonl"

# Configuration (sera loadée depuis .env en production)
SHAREHOLDER_PHONE = os.getenv("SHAREHOLDER_PHONE", "+33XXXXXXXXX")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")


class HotVisitWebhook(BaseModel):
    """Webhook payload pour visite de page critique"""
    ip: str
    page: str  # /pricing, /trial-signup, /trial-14d, etc.
    timestamp: str
    user_agent: Optional[str] = None
    referrer: Optional[str] = None


def load_known_leads() -> dict:
    """
    Charge la base de leads connus depuis tous les fichiers JSON de croissance.
    Retourne un mapping IP -> lead_info
    """
    ip_to_lead = {}

    # Liste des fichiers de leads à charger
    lead_files = [
        "hn_leads_final_20260960.json",
        "hn_leads_enriched_20260960.json",
        "hot_leads_detected.json",
        "relance_15_leads_trial_direct_20260209.json",
        "automation_relance_leads.json",
    ]

    for filename in lead_files:
        filepath = os.path.join(LEADS_DATA_DIR, filename)
        if not os.path.exists(filepath):
            continue

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Traiter selon la structure
            if isinstance(data, dict) and "leads" in data:
                # Structure: {"leads": [...]}
                for lead in data["leads"]:
                    if isinstance(lead, dict) and "ip" in lead:
                        ip = lead["ip"]
                        ip_to_lead[ip] = {
                            "source_file": filename,
                            "email": lead.get("email", "unknown"),
                            "page": lead.get("page", "unknown"),
                            "first_seen": lead.get("timestamp", lead.get("detected_at", "unknown"))
                        }
            elif isinstance(data, list):
                # Structure: [{"lead": {...}, "email": {...}}]
                for item in data:
                    if isinstance(item, dict):
                        lead_data = item.get("lead", item)
                        # On n'a pas toujours d'IP dans les leads HN (il faut enrichir)
                        # Pour l'instant on stocke l'email comme clé
                        email = lead_data.get("primary_contact") or lead_data.get("email")
                        if email:
                            ip_to_lead[email] = {
                                "source_file": filename,
                                "username": lead_data.get("username", "unknown"),
                                "email": email,
                                "engagement_score": lead_data.get("engagement_score", 0)
                            }
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
            continue

    return ip_to_lead


def match_lead(ip: str, page: str, user_agent: str = None) -> Optional[dict]:
    """
    Croise l'IP avec la base de leads.
    Retourne les infos du lead si match, None sinon.
    """
    known_leads = load_known_leads()

    # Match direct par IP
    if ip in known_leads:
        return known_leads[ip]

    # TODO: Ajouter matching par user-agent fingerprint si nécessaire
    # TODO: Ajouter matching par cookie/session si tracking implémenté

    return None


def send_sms_alert(lead_info: dict, page: str, ip: str) -> bool:
    """
    Envoie un SMS via Twilio à l'actionnaire.
    Retourne True si succès, False sinon.
    """
    # Vérifier que Twilio est configuré
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
        print("WARNING: Twilio credentials not configured - SMS not sent")
        return False

    try:
        # Import Twilio uniquement si credentials présents
        from twilio.rest import Client

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Construire le message
        lead_email = lead_info.get("email", "unknown")
        lead_username = lead_info.get("username", "unknown")

        message_body = (
            f"🔥 HOT LEAD ALERT!\n\n"
            f"Lead: {lead_email}\n"
            f"Page: {page}\n"
            f"IP: {ip}\n"
            f"Time: {datetime.now(timezone.utc).strftime('%H:%M UTC')}\n\n"
            f"Action requise: Relance immédiate!"
        )

        message = client.messages.create(
            body=message_body,
            from_=TWILIO_FROM_NUMBER,
            to=SHAREHOLDER_PHONE
        )

        print(f"SMS sent successfully - SID: {message.sid}")
        return True

    except ImportError:
        print("WARNING: Twilio library not installed - run: pip install twilio")
        return False
    except Exception as e:
        print(f"ERROR sending SMS: {e}")
        return False


def log_alert(ip: str, page: str, lead_info: dict, sms_sent: bool):
    """Log l'alerte dans le fichier de tracking"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "page": page,
        "lead_info": lead_info,
        "sms_sent": sms_sent,
        "alert_type": "hot_visit"
    }

    try:
        # Créer le répertoire si nécessaire
        os.makedirs(os.path.dirname(ALERTS_LOG), exist_ok=True)

        with open(ALERTS_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"WARNING: Could not log alert: {e}")


@router.post("/api/alert-hot-visit")
async def alert_hot_visit(webhook: HotVisitWebhook, request: Request):
    """
    Endpoint webhook pour alertes SMS temps-réel.

    Flow:
    1. Reçoit webhook visite page (IP, page, timestamp)
    2. Croise avec base leads (email<>IP matching)
    3. Si match lead connu + page critique → SMS actionnaire

    Pages critiques: /pricing, /trial-signup, /trial-14d
    """
    # Vérifier que la page est critique
    critical_pages = ["/pricing", "/trial-signup", "/trial-14d", "/trial-14d.html"]

    if webhook.page not in critical_pages:
        return {
            "status": "ignored",
            "reason": f"Page {webhook.page} is not critical",
            "critical_pages": critical_pages
        }

    # Matching lead
    lead_info = match_lead(
        ip=webhook.ip,
        page=webhook.page,
        user_agent=webhook.user_agent
    )

    if not lead_info:
        return {
            "status": "no_match",
            "message": "Visitor IP not found in known leads database",
            "ip": webhook.ip
        }

    # Lead connu + page critique = ALERTE SMS
    sms_sent = send_sms_alert(lead_info, webhook.page, webhook.ip)

    # Log l'alerte
    log_alert(webhook.ip, webhook.page, lead_info, sms_sent)

    return {
        "status": "alert_sent" if sms_sent else "alert_logged",
        "lead": lead_info.get("email", "unknown"),
        "page": webhook.page,
        "sms_sent": sms_sent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/api/alert-hot-visit/health")
async def health_check():
    """Health check de l'endpoint"""
    twilio_configured = all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER])

    # Compter les leads connus
    known_leads = load_known_leads()

    # Compter les alertes envoyées
    alert_count = 0
    if os.path.exists(ALERTS_LOG):
        try:
            with open(ALERTS_LOG, 'r') as f:
                alert_count = sum(1 for _ in f)
        except Exception:
            pass

    return {
        "status": "healthy",
        "twilio_configured": twilio_configured,
        "known_leads_count": len(known_leads),
        "total_alerts_sent": alert_count,
        "alerts_log_path": ALERTS_LOG,
        "shareholder_phone": SHAREHOLDER_PHONE if twilio_configured else "not_configured"
    }


@router.get("/api/alert-hot-visit/stats")
async def get_stats():
    """Statistiques des alertes envoyées"""
    if not os.path.exists(ALERTS_LOG):
        return {
            "total_alerts": 0,
            "alerts_by_page": {},
            "alerts_by_lead": {},
            "sms_success_rate": 0
        }

    try:
        alerts = []
        with open(ALERTS_LOG, 'r') as f:
            for line in f:
                alerts.append(json.loads(line))

        # Statistiques
        alerts_by_page = {}
        alerts_by_lead = {}
        sms_sent_count = 0

        for alert in alerts:
            page = alert["page"]
            lead_email = alert["lead_info"].get("email", "unknown")

            alerts_by_page[page] = alerts_by_page.get(page, 0) + 1
            alerts_by_lead[lead_email] = alerts_by_lead.get(lead_email, 0) + 1

            if alert["sms_sent"]:
                sms_sent_count += 1

        return {
            "total_alerts": len(alerts),
            "alerts_by_page": alerts_by_page,
            "alerts_by_lead": alerts_by_lead,
            "sms_success_rate": round(sms_sent_count / len(alerts) * 100, 1) if alerts else 0,
            "last_alert": alerts[-1] if alerts else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading stats: {str(e)}")
