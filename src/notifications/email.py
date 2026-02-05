"""Email notification system using msmtp Docker"""
import subprocess
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class EmailConfig:
    from_address: str = "contact@arkforge.fr"
    from_name: str = "ArkWatch"


class EmailNotifier:
    """Send email notifications via msmtp Docker container"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
    
    def send_alert(self, to: str, watch_name: str, url: str, 
                   summary: str, importance: str, diff: Optional[str] = None) -> bool:
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
        
        body += """---
ArkWatch - Service de veille IA
https://arkforge.fr
"""
        
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
        
        body += """
---
ArkWatch - Service de veille IA
https://arkforge.fr
"""
        
        return self._send_email(to, subject, body)
    
    def _send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email via msmtp Docker"""
        
        email_content = f"""From: {self.config.from_name} <{self.config.from_address}>
To: {to}
Subject: {subject}
Content-Type: text/plain; charset=utf-8

{body}"""
        
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "-i", "msmtp-mailer:latest", 
                 "--read-recipients", "--read-envelope-from"],
                input=email_content.encode("utf-8"),
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
