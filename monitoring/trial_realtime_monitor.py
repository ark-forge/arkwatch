#!/usr/bin/env python3
"""
Real-time Trial /trial-14d Silent Bug Detector
Monitors every 5min for conversion-blocking bugs
GARDIEN TASK #20261124 - 2026-02-10
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# Add automation directory for email sender
sys.path.insert(0, "/opt/claude-ceo/automation")

try:
    from email_sender import send_email, count_emails_today, load_config
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# Configuration
MONITOR_INTERVAL = 300  # 5 minutes
ALERT_EMAIL = "apps.desiorac@gmail.com"
API_BASE_URL = "http://127.0.0.1:8080"

# File paths
TRIAL_TRACKING_PATH = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_signups.json"
EMAIL_TRACKING_PATH = "/opt/claude-ceo/workspace/croissance/email_tracking.json"
WARMUP_LOG_PATH = "/opt/claude-ceo/workspace/memory/warmup_log.json"
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/monitoring/monitor_state.json"
ALERT_LOG = "/opt/claude-ceo/workspace/arkwatch/monitoring/alerts.log"
BUG_REPORT = "/opt/claude-ceo/workspace/gardien/RAPPORT_BUGS_TRIAL_14D_20261124.md"

# Alert thresholds
MAX_PAGE_LOAD_TIME_MS = 3000  # 3s
MAX_EMAIL_BOUNCE_RATE = 20  # 20%
MIN_EMAIL_SEND_RATE = 80  # 80%
EMAIL_WARMUP_LIMIT = 30  # Daily limit


class TrialRealtimeMonitor:
    """Real-time monitoring for silent bugs blocking trial conversion"""

    def __init__(self):
        self.state = self.load_state()
        self.bugs_found = []
        self.alerts = []
        self.start_time = datetime.now(timezone.utc)

    def load_state(self) -> Dict:
        """Load monitoring state"""
        if Path(STATE_FILE).exists():
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        return {
            "last_check": None,
            "total_checks": 0,
            "total_alerts": 0,
            "total_bugs_found": 0,
            "bugs_detected": [],
        }

    def save_state(self):
        """Save monitoring state"""
        self.state["last_check"] = datetime.now(timezone.utc).isoformat()
        self.state["total_checks"] += 1
        self.state["total_bugs_found"] = self.state.get("total_bugs_found", 0) + len(self.bugs_found)

        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(STATE_FILE).with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        tmp.replace(STATE_FILE)

    def log_alert(self, severity: str, bug_type: str, message: str, evidence: Dict):
        """Log alert"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "bug_type": bug_type,
            "message": message,
            "evidence": evidence,
        }

        self.alerts.append(alert)
        self.state["total_alerts"] += 1

        # Append to log
        Path(ALERT_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(ALERT_LOG, "a") as f:
            f.write(json.dumps(alert) + "\n")

        # Track unique bugs
        if bug_type not in [b["type"] for b in self.state["bugs_detected"]]:
            self.state["bugs_detected"].append({
                "type": bug_type,
                "first_detected": alert["timestamp"],
                "severity": severity,
            })

    def check_api_health(self) -> List[Dict]:
        """Check API /health endpoint and response time"""
        bugs = []

        try:
            start = time.time()
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            response_time_ms = int((time.time() - start) * 1000)

            if response.status_code != 200:
                self.log_alert(
                    "CRITICAL",
                    "api_health_down",
                    f"API /health returned {response.status_code}",
                    {"status_code": response.status_code, "url": f"{API_BASE_URL}/health"},
                )
                bugs.append({
                    "type": "api_health_down",
                    "status_code": response.status_code,
                    "response_time_ms": response_time_ms,
                })

            if response_time_ms > MAX_PAGE_LOAD_TIME_MS:
                self.log_alert(
                    "HIGH",
                    "api_slow_response",
                    f"API /health took {response_time_ms}ms (threshold: {MAX_PAGE_LOAD_TIME_MS}ms)",
                    {"response_time_ms": response_time_ms, "threshold": MAX_PAGE_LOAD_TIME_MS},
                )
                bugs.append({
                    "type": "api_slow_response",
                    "response_time_ms": response_time_ms,
                    "threshold": MAX_PAGE_LOAD_TIME_MS,
                })

        except requests.exceptions.Timeout:
            self.log_alert(
                "CRITICAL",
                "api_timeout",
                "API /health endpoint timeout (>5s)",
                {"timeout": 5000},
            )
            bugs.append({"type": "api_timeout", "timeout_ms": 5000})

        except requests.exceptions.ConnectionError as e:
            self.log_alert(
                "CRITICAL",
                "api_connection_error",
                f"Cannot connect to API: {e}",
                {"error": str(e), "url": API_BASE_URL},
            )
            bugs.append({"type": "api_connection_error", "error": str(e)})

        return bugs

    def check_trial_endpoint(self) -> List[Dict]:
        """Check /trial-signup/stats endpoint for errors"""
        bugs = []

        try:
            start = time.time()
            response = requests.get(f"{API_BASE_URL}/trial-signup/stats", timeout=5)
            response_time_ms = int((time.time() - start) * 1000)

            if response.status_code != 200:
                self.log_alert(
                    "CRITICAL",
                    "trial_endpoint_error",
                    f"/trial-signup/stats returned {response.status_code}",
                    {"status_code": response.status_code},
                )
                bugs.append({
                    "type": "trial_endpoint_error",
                    "status_code": response.status_code,
                    "response_time_ms": response_time_ms,
                })
            else:
                # Check response data
                data = response.json()

                # Bug: Low email send rate
                if data.get("total_submissions", 0) > 0:
                    send_rate = data.get("email_send_rate", 0)
                    if send_rate < MIN_EMAIL_SEND_RATE:
                        self.log_alert(
                            "CRITICAL",
                            "low_email_send_rate_api",
                            f"Email send rate is {send_rate}% (threshold: {MIN_EMAIL_SEND_RATE}%)",
                            data,
                        )
                        bugs.append({
                            "type": "low_email_send_rate_api",
                            "send_rate": send_rate,
                            "data": data,
                        })

        except Exception as e:
            self.log_alert(
                "HIGH",
                "trial_endpoint_exception",
                f"Error checking /trial-signup/stats: {e}",
                {"error": str(e)},
            )
            bugs.append({"type": "trial_endpoint_exception", "error": str(e)})

        return bugs

    def check_email_warmup_limit(self) -> List[Dict]:
        """CRITICAL: Check if warmup limit blocks trial emails"""
        bugs = []

        if not EMAIL_ENABLED:
            return bugs

        try:
            config = load_config()
            emails_today = count_emails_today(exclude_shareholder=True)

            # CRITICAL BUG: Warmup limit reached
            if emails_today >= EMAIL_WARMUP_LIMIT:
                self.log_alert(
                    "CRITICAL",
                    "email_warmup_limit_reached",
                    f"Email warmup limit reached: {emails_today}/{EMAIL_WARMUP_LIMIT} emails sent today. ALL TRIAL EMAILS BLOCKED.",
                    {
                        "emails_today": emails_today,
                        "limit": EMAIL_WARMUP_LIMIT,
                        "impact": "ALL trial confirmation emails are silently blocked",
                        "file": "email_sender.py:114",
                        "action": "Increase WARMUP_LIMIT or exclude trial emails from warmup",
                    },
                )
                bugs.append({
                    "type": "email_warmup_limit_reached",
                    "emails_today": emails_today,
                    "limit": EMAIL_WARMUP_LIMIT,
                    "blocked": True,
                })

            # WARNING: Approaching limit
            elif emails_today >= EMAIL_WARMUP_LIMIT * 0.8:
                self.log_alert(
                    "HIGH",
                    "email_warmup_limit_warning",
                    f"Email warmup limit at {emails_today}/{EMAIL_WARMUP_LIMIT} ({emails_today/EMAIL_WARMUP_LIMIT*100:.0f}%). Trial emails may be blocked soon.",
                    {
                        "emails_today": emails_today,
                        "limit": EMAIL_WARMUP_LIMIT,
                        "percentage": round(emails_today / EMAIL_WARMUP_LIMIT * 100, 1),
                    },
                )
                bugs.append({
                    "type": "email_warmup_limit_warning",
                    "emails_today": emails_today,
                    "limit": EMAIL_WARMUP_LIMIT,
                })

        except Exception as e:
            self.log_alert(
                "MEDIUM",
                "email_warmup_check_error",
                f"Error checking email warmup: {e}",
                {"error": str(e)},
            )

        return bugs

    def check_trial_tracking_data(self) -> List[Dict]:
        """Check trial_signups_tracking.json for submission issues"""
        bugs = []

        if not Path(TRIAL_TRACKING_PATH).exists():
            self.log_alert(
                "HIGH",
                "trial_tracking_file_missing",
                "Trial tracking file not found",
                {"path": TRIAL_TRACKING_PATH},
            )
            return bugs

        try:
            with open(TRIAL_TRACKING_PATH) as f:
                data = json.load(f)

            submissions = data.get("submissions", [])
            total = len(submissions)

            if total == 0:
                # No submissions yet, not a bug
                return bugs

            # Check email send failures
            emails_sent = sum(1 for s in submissions if s.get("email_sent"))
            send_rate = (emails_sent / total * 100) if total > 0 else 0

            if send_rate < MIN_EMAIL_SEND_RATE:
                failed_submissions = [s for s in submissions if not s.get("email_sent")]
                self.log_alert(
                    "CRITICAL",
                    "trial_email_send_failures",
                    f"{len(failed_submissions)}/{total} trial emails failed to send ({send_rate:.1f}%)",
                    {
                        "total_submissions": total,
                        "emails_sent": emails_sent,
                        "send_rate": send_rate,
                        "failed_count": len(failed_submissions),
                        "sample_failed": failed_submissions[:3],
                    },
                )
                bugs.append({
                    "type": "trial_email_send_failures",
                    "failed_count": len(failed_submissions),
                    "total": total,
                    "send_rate": send_rate,
                })

            # Check for recent submissions without email (< 24h)
            now = datetime.now(timezone.utc)
            recent_no_email = []
            for s in submissions:
                submitted_at = datetime.fromisoformat(s["submitted_at"].replace("Z", "+00:00"))
                age_hours = (now - submitted_at).total_seconds() / 3600

                if age_hours < 24 and not s.get("email_sent"):
                    recent_no_email.append({
                        "email": s["email"],
                        "submitted_at": s["submitted_at"],
                        "age_hours": round(age_hours, 1),
                    })

            if recent_no_email:
                self.log_alert(
                    "HIGH",
                    "recent_trial_no_email",
                    f"{len(recent_no_email)} trial submissions in last 24h did not receive confirmation email",
                    {"failed_recent": recent_no_email},
                )
                bugs.append({
                    "type": "recent_trial_no_email",
                    "count": len(recent_no_email),
                    "submissions": recent_no_email,
                })

        except Exception as e:
            self.log_alert(
                "MEDIUM",
                "trial_tracking_read_error",
                f"Error reading trial tracking: {e}",
                {"error": str(e)},
            )

        return bugs

    def check_form_submission_flow(self) -> List[Dict]:
        """Test trial-signup POST endpoint (dry run check)"""
        bugs = []

        # We don't want to spam test submissions, but we can check if endpoint is reachable
        try:
            # Try OPTIONS request to check CORS
            response = requests.options(f"{API_BASE_URL}/trial-signup", timeout=3)

            # Check if POST is allowed
            if response.status_code == 200:
                allowed_methods = response.headers.get("Allow", "").split(",")
                if "POST" not in [m.strip().upper() for m in allowed_methods]:
                    self.log_alert(
                        "HIGH",
                        "trial_signup_post_disabled",
                        "POST method not allowed on /trial-signup endpoint",
                        {"allowed_methods": allowed_methods},
                    )
                    bugs.append({
                        "type": "trial_signup_post_disabled",
                        "allowed_methods": allowed_methods,
                    })

        except Exception as e:
            # OPTIONS might not be supported, not critical
            pass

        return bugs

    def run_all_checks(self) -> Dict:
        """Run all monitoring checks"""
        print(f"[{self.start_time.isoformat()}] Starting trial monitoring checks...")
        print("=" * 80)

        # Run checks
        self.bugs_found.extend(self.check_api_health())
        self.bugs_found.extend(self.check_trial_endpoint())
        self.bugs_found.extend(self.check_email_warmup_limit())  # CRITICAL CHECK
        self.bugs_found.extend(self.check_trial_tracking_data())
        self.bugs_found.extend(self.check_form_submission_flow())

        # Generate report
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "total_bugs_found": len(self.bugs_found),
            "bugs": self.bugs_found,
            "alerts": self.alerts,
            "state": self.state,
            "summary": {
                "critical_bugs": len([b for b in self.bugs_found if any(a["severity"] == "CRITICAL" for a in self.alerts if a["bug_type"] == b["type"])]),
                "high_bugs": len([b for b in self.bugs_found if any(a["severity"] == "HIGH" for a in self.alerts if a["bug_type"] == b["type"])]),
                "medium_bugs": len([b for b in self.bugs_found if any(a["severity"] == "MEDIUM" for a in self.alerts if a["bug_type"] == b["type"])]),
            },
        }

        # Save state
        self.save_state()

        return report

    def generate_markdown_report(self, report: Dict) -> str:
        """Generate detailed markdown bug report"""
        md = f"""# RAPPORT BUGS TRIAL /trial-14d - Monitoring Temps Réel

**Date**: {report['timestamp']}
**Durée analyse**: {report['duration_seconds']:.2f}s
**Bugs détectés**: {report['total_bugs_found']}
**CRITICAL**: {report['summary']['critical_bugs']} | **HIGH**: {report['summary']['high_bugs']} | **MEDIUM**: {report['summary']['medium_bugs']}

---

## RÉSUMÉ EXÉCUTIF

"""
        if report['total_bugs_found'] == 0:
            md += "✅ **Aucun bug détecté** - Système trial fonctionnel.\n\n"
        else:
            md += f"⚠️ **{report['total_bugs_found']} bugs détectés bloquant la conversion trial**\n\n"

            # Critical bugs first
            critical_alerts = [a for a in report['alerts'] if a['severity'] == 'CRITICAL']
            if critical_alerts:
                md += "### 🚨 BUGS CRITIQUES (action immédiate requise)\n\n"
                for alert in critical_alerts:
                    md += f"**{alert['bug_type']}**\n"
                    md += f"- {alert['message']}\n"
                    md += f"- Preuve: `{json.dumps(alert['evidence'], indent=2)}`\n\n"

        md += "\n---\n\n## DÉTAIL DES BUGS DÉTECTÉS\n\n"

        for i, bug in enumerate(report['bugs'], 1):
            alert = next((a for a in report['alerts'] if a['bug_type'] == bug['type']), None)
            if alert:
                md += f"### BUG #{i}: {bug['type']}\n\n"
                md += f"**Sévérité**: {alert['severity']}\n"
                md += f"**Message**: {alert['message']}\n"
                md += f"**Timestamp**: {alert['timestamp']}\n\n"
                md += "**Preuve**:\n```json\n"
                md += json.dumps(alert['evidence'], indent=2)
                md += "\n```\n\n"
                md += "**Données bug**:\n```json\n"
                md += json.dumps(bug, indent=2)
                md += "\n```\n\n"
                md += "---\n\n"

        md += "## ÉTAT DU MONITORING\n\n"
        md += f"- **Total checks exécutés**: {self.state['total_checks']}\n"
        md += f"- **Total alertes générées**: {self.state['total_alerts']}\n"
        md += f"- **Total bugs trouvés (all-time)**: {self.state['total_bugs_found']}\n"
        md += f"- **Dernier check**: {self.state['last_check']}\n\n"

        md += "## PROCHAINES ACTIONS\n\n"
        if report['total_bugs_found'] > 0:
            md += "1. Corriger bugs CRITICAL en priorité\n"
            md += "2. Redémarrer services si nécessaire\n"
            md += "3. Vérifier conversion trial après correction\n"
            md += "4. Monitorer pendant 24h pour confirmer résolution\n"
        else:
            md += "Aucune action requise - Continuer monitoring.\n"

        md += f"\n---\n\n**Rapport généré par**: Gardien Worker  \n"
        md += f"**Task**: #20261124  \n"
        md += f"**Monitoring interval**: {MONITOR_INTERVAL}s (5min)  \n"

        return md


def main():
    """Main monitoring execution"""
    monitor = TrialRealtimeMonitor()

    print("=" * 80)
    print("TRIAL /trial-14d REAL-TIME MONITORING - SILENT BUG DETECTOR")
    print("=" * 80)
    print(f"Task: #20261124 | Worker: GARDIEN")
    print(f"Interval: {MONITOR_INTERVAL}s (5min)")
    print(f"Alert email: {ALERT_EMAIL}")
    print("=" * 80)
    print()

    # Run checks
    report = monitor.run_all_checks()

    # Display results
    print()
    print("=" * 80)
    print("RÉSULTATS")
    print("=" * 80)
    print(f"✓ Checks exécutés en {report['duration_seconds']:.2f}s")
    print(f"✓ Bugs détectés: {report['total_bugs_found']}")
    print(f"  - CRITICAL: {report['summary']['critical_bugs']}")
    print(f"  - HIGH: {report['summary']['high_bugs']}")
    print(f"  - MEDIUM: {report['summary']['medium_bugs']}")
    print()

    if report['total_bugs_found'] > 0:
        print("⚠️  BUGS DÉTECTÉS:")
        for bug in report['bugs']:
            bug_type = bug['type']
            alert = next((a for a in report['alerts'] if a['bug_type'] == bug_type), None)
            severity = alert['severity'] if alert else 'UNKNOWN'
            print(f"   [{severity}] {bug_type}")
        print()

    # Generate markdown report
    md_report = monitor.generate_markdown_report(report)

    # Save markdown report
    Path(BUG_REPORT).parent.mkdir(parents=True, exist_ok=True)
    with open(BUG_REPORT, "w") as f:
        f.write(md_report)

    print(f"✓ Rapport détaillé sauvegardé: {BUG_REPORT}")
    print(f"✓ Alertes loggées: {ALERT_LOG}")
    print(f"✓ État monitoring: {STATE_FILE}")
    print()

    # Save JSON report
    json_report_file = f"/opt/claude-ceo/workspace/gardien/report_trial_bugs_{int(time.time())}.json"
    with open(json_report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"✓ Rapport JSON: {json_report_file}")
    print()

    print("=" * 80)
    print("MONITORING TERMINÉ")
    print("=" * 80)

    # Return exit code
    return 0 if report['total_bugs_found'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
