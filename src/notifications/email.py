"""Email notification system using email_sender.py"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

EMAIL_SENDER_PATH = "/opt/claude-ceo/automation/email_sender.py"
UNSUBSCRIBE_BASE_URL = "https://watch.arkforge.fr/api/v1/auth/unsubscribe"


@dataclass
class EmailConfig:
    from_address: str = "contact@arkforge.fr"
    from_name: str = "ArkWatch"


class EmailNotifier:
    """Send email notifications via email_sender.py"""

    def __init__(self, config: EmailConfig | None = None):
        self.config = config or EmailConfig()

    def _unsubscribe_link(self, email: str) -> str:
        """Generate an unsubscribe link for the given email."""
        from ..api.auth import generate_unsubscribe_token

        token = generate_unsubscribe_token(email)
        return f"{UNSUBSCRIBE_BASE_URL}?email={quote(email)}&token={token}"

    def _footer(self, email: str) -> str:
        """Standard email footer with unsubscribe link."""
        link = self._unsubscribe_link(email)
        return (
            f"---\nArkWatch - Service de veille IA\nhttps://arkforge.fr\n\nSe désinscrire des notifications: {link}\n"
        )

    def send_alert(
        self, to: str, watch_name: str, url: str, summary: str, importance: str, diff: str | None = None
    ) -> bool:
        """Send an alert email about changes detected"""

        importance_emoji = {
            "low": "📋",
            "medium": "📢",
            "high": "⚠️",
            "critical": "🚨",
        }.get(importance, "📋")

        subject = f"{importance_emoji} [{importance.upper()}] Changements détectés: {watch_name}"

        body = f"""Bonjour,

ArkWatch a détecté des changements sur une page que vous surveillez.

=== DÉTAILS ===

📍 Surveillance: {watch_name}
🔗 URL: {url}
⏰ Détecté le: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
📊 Importance: {importance.upper()}

=== RÉSUMÉ IA ===

{summary}

"""

        if diff:
            body += f"""=== MODIFICATIONS ===

{diff[:1000]}
{"[...tronqué...]" if len(diff) > 1000 else ""}

"""

        body += self._footer(to)

        return self._send_email(to, subject, body)

    def send_daily_digest(self, to: str, reports: list) -> bool:
        """Send daily digest of all changes"""

        if not reports:
            return True  # Nothing to send

        subject = f"📊 ArkWatch - Rapport quotidien ({len(reports)} changements)"

        body = f"""Bonjour,

Voici votre rapport quotidien ArkWatch.

=== RÉSUMÉ ===

📈 Changements détectés: {len(reports)}
📅 Date: {datetime.utcnow().strftime("%Y-%m-%d")}

=== DÉTAILS ===

"""

        for i, report in enumerate(reports[:10], 1):
            body += f"""
{i}. {report.get("watch_name", "Surveillance")}
   URL: {report.get("url", "N/A")}
   Importance: {report.get("ai_importance", "medium")}
   Résumé: {report.get("ai_summary", "Changements détectés")}

"""

        if len(reports) > 10:
            body += f"\n... et {len(reports) - 10} autres changements.\n"

        body += "\n" + self._footer(to)

        return self._send_email(to, subject, body)

    def _send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email via email_sender.py (SMTP OVH)"""
        try:
            result = subprocess.run(
                ["python3", EMAIL_SENDER_PATH, to, subject, body],
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0:
                print(f"Email sent to {to}")
                return True
            else:
                print(f"Email error: {result.stderr.decode()}")
                return False

        except Exception as e:
            print(f"Email exception: {e}")
            return False


# Test
def test_notifier():
    notifier = EmailNotifier()
    success = notifier.send_alert(
        to="apps.desiorac@gmail.com",
        watch_name="Test Watch",
        url="https://example.com",
        summary="Ceci est un test du système de notification ArkWatch.",
        importance="medium",
    )
    print(f"Test email sent: {success}")


if __name__ == "__main__":
    test_notifier()
