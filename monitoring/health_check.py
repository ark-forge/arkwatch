#!/usr/bin/env python3
"""
ArkWatch & ArkForge Health Check Monitor
Runs every 2min via cron. Alerts via email if downtime > 5min (3 consecutive failures).
Generates status JSON for public status page.

GARDIEN TASK #316 - 2026-02-11
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

# Email sender
sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# === Configuration ===
ALERT_EMAIL = "apps.desiorac@gmail.com"
CONSECUTIVE_FAILURES_ALERT = 3  # 3 x 2min = 6min > 5min threshold
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/monitoring/health_state.json"
STATUS_JSON = "/var/www/arkforge/status.json"
LOG_FILE = "/opt/claude-ceo/workspace/arkwatch/monitoring/health_check.log"

# Endpoints to check
ENDPOINTS = [
    {
        "name": "ArkWatch API",
        "url": "https://watch.arkforge.fr/health",
        "expect_json": {"status": "healthy"},
        "timeout": 10,
    },
    {
        "name": "ArkWatch API (local)",
        "url": "http://127.0.0.1:8080/health",
        "expect_json": {"status": "healthy"},
        "timeout": 5,
        "internal": True,  # not shown on public status page
    },
    {
        "name": "ArkForge Website",
        "url": "https://arkforge.fr/",
        "expect_status": 200,
        "timeout": 10,
    },
    {
        "name": "ArkWatch Ready",
        "url": "https://watch.arkforge.fr/ready",
        "expect_json": {"status": "ready"},
        "timeout": 10,
    },
]


def log(msg):
    """Append to log file with timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
        # Rotate log if > 500KB
        if os.path.getsize(LOG_FILE) > 500_000:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
            with open(LOG_FILE, "w") as f:
                f.writelines(lines[-1000:])
    except Exception:
        pass


def load_state():
    """Load persistent state (failure counts, last alert time)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"endpoints": {}, "last_alert_sent": None}


def save_state(state):
    """Save persistent state."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        log(f"ERROR saving state: {e}")


def check_endpoint(ep):
    """Check a single endpoint. Returns (ok, response_ms, error_msg)."""
    try:
        start = time.time()
        resp = requests.get(ep["url"], timeout=ep["timeout"], verify=True)
        elapsed_ms = round((time.time() - start) * 1000)

        # Check status code
        expected_status = ep.get("expect_status", 200)
        if resp.status_code != expected_status:
            return False, elapsed_ms, f"HTTP {resp.status_code} (expected {expected_status})"

        # Check JSON body if expected
        if "expect_json" in ep:
            try:
                body = resp.json()
                for key, val in ep["expect_json"].items():
                    if body.get(key) != val:
                        return False, elapsed_ms, f"JSON mismatch: {key}={body.get(key)} (expected {val})"
            except ValueError:
                return False, elapsed_ms, "Invalid JSON response"

        return True, elapsed_ms, None

    except requests.exceptions.Timeout:
        return False, ep["timeout"] * 1000, "Timeout"
    except requests.exceptions.ConnectionError as e:
        return False, 0, f"Connection error: {str(e)[:100]}"
    except Exception as e:
        return False, 0, f"Error: {str(e)[:100]}"


def send_alert(endpoint_name, consecutive_failures, error_msg, state):
    """Send email alert for downtime."""
    if not EMAIL_ENABLED:
        log(f"ALERT: Email not available - {endpoint_name} DOWN ({consecutive_failures} failures)")
        return

    # Throttle: max 1 alert per 30min per endpoint
    ep_state = state["endpoints"].get(endpoint_name, {})
    last_alert = ep_state.get("last_alert_sent")
    if last_alert:
        try:
            last_dt = datetime.fromisoformat(last_alert)
            if (datetime.now(timezone.utc) - last_dt).total_seconds() < 1800:
                log(f"ALERT throttled for {endpoint_name} (last alert < 30min ago)")
                return
        except (ValueError, TypeError):
            pass

    downtime_min = consecutive_failures * 2  # 2min intervals
    subject = f"[ALERTE] {endpoint_name} DOWN - {downtime_min}min de downtime"
    body = f"""ALERTE DOWNTIME - ArkForge Monitoring

Endpoint: {endpoint_name}
Status: DOWN
Downtime estimé: ~{downtime_min} minutes
Échecs consécutifs: {consecutive_failures}
Dernière erreur: {error_msg}
Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Action requise: Vérifier le service et redémarrer si nécessaire.

-- ArkForge Health Monitor (Gardien)
"""

    try:
        send_email(ALERT_EMAIL, subject, body, skip_warmup=True)
        ep_state["last_alert_sent"] = datetime.now(timezone.utc).isoformat()
        state["endpoints"][endpoint_name] = ep_state
        log(f"ALERT EMAIL sent for {endpoint_name}")
    except Exception as e:
        log(f"ALERT EMAIL FAILED for {endpoint_name}: {e}")


def send_recovery_alert(endpoint_name, downtime_failures):
    """Send recovery notification."""
    if not EMAIL_ENABLED:
        return
    downtime_min = downtime_failures * 2
    subject = f"[RECOVERY] {endpoint_name} UP - retour après ~{downtime_min}min"
    body = f"""RECOVERY - ArkForge Monitoring

Endpoint: {endpoint_name}
Status: UP (recovered)
Downtime estimé: ~{downtime_min} minutes
Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Le service est de nouveau opérationnel.

-- ArkForge Health Monitor (Gardien)
"""
    try:
        send_email(ALERT_EMAIL, subject, body, skip_warmup=True)
        log(f"RECOVERY EMAIL sent for {endpoint_name}")
    except Exception:
        pass


def generate_status_json(results, state):
    """Generate public status JSON for status page."""
    now = datetime.now(timezone.utc).isoformat()
    services = []
    overall = "operational"

    for ep, (ok, response_ms, error_msg) in results.items():
        # Skip internal endpoints
        ep_config = next((e for e in ENDPOINTS if e["name"] == ep), {})
        if ep_config.get("internal"):
            continue

        ep_state = state["endpoints"].get(ep, {})
        consecutive = ep_state.get("consecutive_failures", 0)

        if not ok:
            if consecutive >= CONSECUTIVE_FAILURES_ALERT:
                status = "major_outage"
                overall = "major_outage"
            else:
                status = "degraded"
                if overall == "operational":
                    overall = "degraded"
        else:
            status = "operational"

        services.append({
            "name": ep,
            "status": status,
            "response_ms": response_ms,
            "last_check": now,
        })

    status_data = {
        "overall": overall,
        "last_updated": now,
        "services": services,
    }

    try:
        with open(STATUS_JSON, "w") as f:
            json.dump(status_data, f, indent=2)
    except IOError as e:
        log(f"ERROR writing status JSON: {e}")


def run_checks():
    """Run all health checks and handle alerts."""
    state = load_state()
    results = {}

    for ep in ENDPOINTS:
        name = ep["name"]
        ok, response_ms, error_msg = check_endpoint(ep)
        results[name] = (ok, response_ms, error_msg)

        if name not in state["endpoints"]:
            state["endpoints"][name] = {"consecutive_failures": 0}

        ep_state = state["endpoints"][name]

        if ok:
            prev_failures = ep_state.get("consecutive_failures", 0)
            if prev_failures >= CONSECUTIVE_FAILURES_ALERT:
                send_recovery_alert(name, prev_failures)
            ep_state["consecutive_failures"] = 0
            ep_state["last_success"] = datetime.now(timezone.utc).isoformat()
            ep_state["last_response_ms"] = response_ms
            log(f"OK: {name} ({response_ms}ms)")
        else:
            ep_state["consecutive_failures"] = ep_state.get("consecutive_failures", 0) + 1
            ep_state["last_failure"] = datetime.now(timezone.utc).isoformat()
            ep_state["last_error"] = error_msg
            consecutive = ep_state["consecutive_failures"]
            log(f"FAIL: {name} ({consecutive}x) - {error_msg}")

            if consecutive >= CONSECUTIVE_FAILURES_ALERT:
                send_alert(name, consecutive, error_msg, state)

        state["endpoints"][name] = ep_state

    save_state(state)
    generate_status_json(results, state)


if __name__ == "__main__":
    run_checks()
