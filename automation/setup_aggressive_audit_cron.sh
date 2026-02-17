#!/bin/bash
# Setup cron pour aggressive_audit_conversion.py
# Exécute toutes les 2 heures pour vérifier et envoyer les emails de la séquence

SCRIPT="/opt/claude-ceo/automation/aggressive_audit_conversion.py"
LOG="/opt/claude-ceo/workspace/arkwatch/data/aggressive_audit_cron.log"
CRON_LINE="0 */2 * * * /usr/bin/python3 $SCRIPT --max-emails 5 >> $LOG 2>&1"

# Vérifier que le script existe
if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: Script not found: $SCRIPT"
    exit 1
fi

# Créer le répertoire de log
mkdir -p "$(dirname "$LOG")"

# Ajouter au crontab si pas déjà présent
if crontab -l 2>/dev/null | grep -q "aggressive_audit_conversion"; then
    echo "Cron already configured for aggressive_audit_conversion.py"
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Cron added: $CRON_LINE"
fi

echo "Setup complete. Logs: $LOG"
echo "Test dry-run: python3 $SCRIPT --dry-run"
echo "Check status: python3 $SCRIPT --status"
