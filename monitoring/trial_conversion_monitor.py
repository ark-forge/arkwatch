#!/usr/bin/env python3
"""
Real-time monitoring system for /trial-14d conversion funnel
Detects silent bugs blocking conversions every 5 minutes
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

# Add automation directory for email sender
sys.path.insert(0, "/opt/claude-ceo/automation")

try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# Configuration
MONITOR_INTERVAL = 300  # 5 minutes
ALERT_EMAIL = "apps.desiorac@gmail.com"
API_LOG_PATH = "/opt/claude-ceo/workspace/arkwatch/logs/api.log"
TRIAL_TRACKING_PATH = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_signups.json"
EMAIL_TRACKING_PATH = "/opt/claude-ceo/workspace/croissance/email_tracking.json"
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/monitoring/monitor_state.json"
ALERT_LOG = "/opt/claude-ceo/workspace/arkwatch/monitoring/alerts.log"

# Alert thresholds
MAX_PAGE_LOAD_TIME = 3000  # 3s in ms
MAX_EMAIL_BOUNCE_RATE = 20  # 20%
MIN_EMAIL_SEND_RATE = 80  # 80% of trials should send email


class TrialConversionMonitor:
    """Monitor /trial-14d conversion funnel for silent bugs"""

    def __init__(self):
        self.state = self.load_state()
        self.alerts = []

    def load_state(self) -> Dict:
        """Load monitoring state from file"""
        if Path(STATE_FILE).exists():
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        # Default state
        return {
            "last_check": None,
            "total_checks": 0,
            "total_alerts": 0,
            "last_alert": None,
            "bugs_detected": [],
        }

    def save_state(self):
        """Save monitoring state to file"""
        self.state["last_check"] = datetime.now(timezone.utc).isoformat()
        self.state["total_checks"] += 1

        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(STATE_FILE).with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        tmp.replace(STATE_FILE)

    def log_alert(self, severity: str, bug_type: str, message: str, evidence: Dict):
        """Log alert to file and memory"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "bug_type": bug_type,
            "message": message,
            "evidence": evidence,
        }

        self.alerts.append(alert)
        self.state["total_alerts"] += 1
        self.state["last_alert"] = alert["timestamp"]

        # Append to alert log
        Path(ALERT_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(ALERT_LOG, "a") as f:
            f.write(json.dumps(alert) + "\n")

        # Add to bugs detected
        if bug_type not in [b["type"] for b in self.state["bugs_detected"]]:
            self.state["bugs_detected"].append({
                "type": bug_type,
                "first_detected": alert["timestamp"],
                "severity": severity,
            })

    def check_api_errors(self) -> List[Dict]:
        """Check API logs for 500 errors on /trial-14d endpoints"""
        bugs = []

        if not Path(API_LOG_PATH).exists():
            self.log_alert(
                "CRITICAL",
                "missing_api_logs",
                "API log file not found - cannot monitor errors",
                {"path": API_LOG_PATH},
            )
            return bugs

        # Read last 1000 lines of API log
        try:
            with open(API_LOG_PATH) as f:
                lines = f.readlines()[-1000:]

            # Look for 500 errors on trial endpoints
            trial_errors = []
            for line in lines:
                if "trial" in line.lower() and ("500" in line or "error" in line.lower()):
                    trial_errors.append(line.strip())

            if trial_errors:
                self.log_alert(
                    "HIGH",
                    "api_500_errors",
                    f"Found {len(trial_errors)} API errors on trial endpoints",
                    {"error_count": len(trial_errors), "sample_errors": trial_errors[:3]},
                )
                bugs.append({
                    "type": "api_500_errors",
                    "count": len(trial_errors),
                    "sample": trial_errors[:3],
                })

        except Exception as e:
            self.log_alert(
                "MEDIUM",
                "log_read_error",
                f"Error reading API logs: {e}",
                {"error": str(e)},
            )

        return bugs

    def check_email_delivery(self) -> List[Dict]:
        """Check email send rate and bounce rate"""
        bugs = []

        if not Path(TRIAL_TRACKING_PATH).exists():
            self.log_alert(
                "HIGH",
                "missing_trial_tracking",
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

            # Check email send rate
            emails_sent = sum(1 for s in submissions if s.get("email_sent"))
            send_rate = (emails_sent / total * 100) if total > 0 else 0

            if send_rate < MIN_EMAIL_SEND_RATE:
                self.log_alert(
                    "CRITICAL",
                    "low_email_send_rate",
                    f"Email send rate is {send_rate:.1f}% (threshold: {MIN_EMAIL_SEND_RATE}%)",
                    {
                        "total_submissions": total,
                        "emails_sent": emails_sent,
                        "send_rate": send_rate,
                        "threshold": MIN_EMAIL_SEND_RATE,
                    },
                )
                bugs.append({
                    "type": "low_email_send_rate",
                    "send_rate": send_rate,
                    "emails_sent": emails_sent,
                    "total": total,
                })

            # Check for recent submissions with no email sent (last 24h)
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
                    "recent_submissions_no_email",
                    f"{len(recent_no_email)} recent submissions (< 24h) did not receive confirmation email",
                    {"failed_emails": recent_no_email},
                )
                bugs.append({
                    "type": "recent_submissions_no_email",
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

    def check_form_submission_rate(self) -> List[Dict]:
        """Check if page visits are converting to form submissions"""
        bugs = []

        # This would require access to page visit tracking
        # For now, we check if submissions exist at all
        if not Path(TRIAL_TRACKING_PATH).exists():
            return bugs

        try:
            with open(TRIAL_TRACKING_PATH) as f:
                data = json.load(f)

            submissions = data.get("submissions", [])

            # Check if there are submissions in last 7 days
            now = datetime.now(timezone.utc)
            recent_submissions = []
            for s in submissions:
                submitted_at = datetime.fromisoformat(s["submitted_at"].replace("Z", "+00:00"))
                age_days = (now - submitted_at).total_seconds() / 86400

                if age_days < 7:
                    recent_submissions.append(s)

            if len(submissions) > 0 and len(recent_submissions) == 0:
                self.log_alert(
                    "HIGH",
                    "no_recent_submissions",
                    "No trial submissions in the last 7 days (but submissions exist historically)",
                    {
                        "total_submissions": len(submissions),
                        "recent_submissions": 0,
                        "last_submission": submissions[-1]["submitted_at"] if submissions else None,
                    },
                )
                bugs.append({
                    "type": "no_recent_submissions",
                    "total": len(submissions),
                    "recent": 0,
                })

        except Exception as e:
            self.log_alert(
                "LOW",
                "submission_rate_check_error",
                f"Error checking submission rate: {e}",
                {"error": str(e)},
            )

        return bugs

    def check_email_bounce_rate(self) -> List[Dict]:
        """Check email bounce rate from email tracking"""
        bugs = []

        if not Path(EMAIL_TRACKING_PATH).exists():
            # Email tracking file might not exist yet
            return bugs

        try:
            with open(EMAIL_TRACKING_PATH) as f:
                data = json.load(f)

            # Look for bounced emails in trial campaigns
            campaigns = data.get("campaigns", {})
            for campaign_id, campaign_data in campaigns.items():
                if "trial" not in campaign_id.lower():
                    continue

                sends = campaign_data.get("sends", [])
                total_sends = len(sends)
                if total_sends == 0:
                    continue

                bounced = sum(1 for s in sends if s.get("bounced", False))
                bounce_rate = (bounced / total_sends * 100) if total_sends > 0 else 0

                if bounce_rate > MAX_EMAIL_BOUNCE_RATE:
                    self.log_alert(
                        "MEDIUM",
                        "high_email_bounce_rate",
                        f"Campaign {campaign_id} has {bounce_rate:.1f}% bounce rate (threshold: {MAX_EMAIL_BOUNCE_RATE}%)",
                        {
                            "campaign_id": campaign_id,
                            "total_sends": total_sends,
                            "bounced": bounced,
                            "bounce_rate": bounce_rate,
                            "threshold": MAX_EMAIL_BOUNCE_RATE,
                        },
                    )
                    bugs.append({
                        "type": "high_email_bounce_rate",
                        "campaign": campaign_id,
                        "bounce_rate": bounce_rate,
                        "bounced": bounced,
                        "total": total_sends,
                    })

        except Exception as e:
            # Not critical if email tracking doesn't exist
            pass

        return bugs

    def run_checks(self) -> Dict:
        """Run all monitoring checks"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Starting monitoring checks...")

        all_bugs = []

        # Run all checks
        all_bugs.extend(self.check_api_errors())
        all_bugs.extend(self.check_email_delivery())
        all_bugs.extend(self.check_form_submission_rate())
        all_bugs.extend(self.check_email_bounce_rate())

        # Generate report
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_bugs_found": len(all_bugs),
            "bugs": all_bugs,
            "alerts": self.alerts,
            "state": self.state,
        }

        # Save state
        self.save_state()

        return report

    def send_alert_email(self, report: Dict):
        """Send alert email to shareholder if critical bugs found"""
        if not EMAIL_ENABLED:
            print("Email not enabled, skipping alert email")
            return

        critical_bugs = [a for a in report["alerts"] if a["severity"] in ["CRITICAL", "HIGH"]]

        if not critical_bugs:
            print("No critical bugs found, skipping alert email")
            return

        subject = f"🚨 URGENT: {len(critical_bugs)} Critical Bugs Detected on /trial-14d Conversion"

        # Format bugs for email
        bugs_html = ""
        for bug in critical_bugs:
            bugs_html += f"""
            <div style="background: #fee; border-left: 4px solid #c00; padding: 15px; margin: 10px 0; border-radius: 4px;">
                <strong style="color: #c00;">{bug['severity']}: {bug['bug_type']}</strong><br>
                <p style="margin: 10px 0;">{bug['message']}</p>
                <pre style="background: #f5f5f5; padding: 10px; overflow-x: auto; font-size: 12px;">{json.dumps(bug['evidence'], indent=2)}</pre>
            </div>
            """

        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: monospace; line-height: 1.6; color: #1a1a1a; max-width: 800px; margin: 0 auto; padding: 20px;">
    <div style="background: #c00; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 24px;">🚨 Critical Bugs Detected</h1>
        <p style="margin: 10px 0 0;">Trial conversion monitoring system found {len(critical_bugs)} critical issues</p>
    </div>

    <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="margin: 0 0 15px;">Summary</h2>
        <ul style="margin: 0; padding-left: 20px;">
            <li>Total bugs detected: <strong>{report['total_bugs_found']}</strong></li>
            <li>Critical/High severity: <strong>{len(critical_bugs)}</strong></li>
            <li>Timestamp: {report['timestamp']}</li>
        </ul>
    </div>

    <h2>Bugs Detected</h2>
    {bugs_html}

    <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 20px;">
        <p style="margin: 0;"><strong>Action Required:</strong> Review and fix these bugs immediately to restore conversion funnel.</p>
        <p style="margin: 10px 0 0;">Full report: /opt/claude-ceo/workspace/arkwatch/monitoring/alerts.log</p>
    </div>
</body>
</html>
"""

        try:
            send_email(
                to_addr=ALERT_EMAIL,
                subject=subject,
                body="Critical bugs detected in trial conversion funnel",
                html_body=html_body,
            )
            print(f"✅ Alert email sent to {ALERT_EMAIL}")
        except Exception as e:
            print(f"❌ Error sending alert email: {e}")


def main():
    """Main monitoring loop"""
    monitor = TrialConversionMonitor()

    print("=" * 80)
    print("Trial Conversion Monitor - Real-time Bug Detection")
    print("=" * 80)
    print(f"Monitoring interval: {MONITOR_INTERVAL}s (5 minutes)")
    print(f"Alert email: {ALERT_EMAIL}")
    print(f"State file: {STATE_FILE}")
    print(f"Alert log: {ALERT_LOG}")
    print("=" * 80)

    # Run first check immediately
    report = monitor.run_checks()

    print(f"\n📊 Check completed: {report['total_bugs_found']} bugs found")
    if report['total_bugs_found'] > 0:
        print(f"⚠️  Bugs detected:")
        for bug in report['bugs']:
            print(f"   - {bug['type']}")

    # Send alert if critical bugs
    if any(a["severity"] in ["CRITICAL", "HIGH"] for a in report["alerts"]):
        print(f"\n🚨 Critical bugs detected, sending alert email...")
        monitor.send_alert_email(report)

    # Save report to file
    report_file = f"/opt/claude-ceo/workspace/arkwatch/monitoring/report_{int(time.time())}.json"
    Path(report_file).parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Report saved: {report_file}")
    print(f"Total checks run: {monitor.state['total_checks']}")
    print(f"Total alerts: {monitor.state['total_alerts']}")

    return 0 if report['total_bugs_found'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
