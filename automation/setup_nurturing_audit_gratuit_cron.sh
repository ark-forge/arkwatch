#!/bin/bash
# Setup cron job for ArkWatch Audit Gratuit Nurturing Sequence
# Runs every hour to send scheduled nurturing emails

SCRIPT_PATH="/opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py"
CRON_JOB="0 * * * * cd /opt/claude-ceo && /usr/bin/python3 $SCRIPT_PATH >> /opt/claude-ceo/workspace/arkwatch/logs/nurturing_audit_gratuit.log 2>&1"

echo "Setting up cron job for Audit Gratuit Nurturing..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "nurturing_audit_gratuit.py"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "nurturing_audit_gratuit.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "Schedule: Every hour (at :00)"
echo "Script: $SCRIPT_PATH"
echo "Logs: /opt/claude-ceo/workspace/arkwatch/logs/nurturing_audit_gratuit.log"
echo ""
echo "To verify:"
echo "  crontab -l | grep nurturing_audit_gratuit"
echo ""
echo "To test manually:"
echo "  python3 $SCRIPT_PATH --dry-run"
echo "  python3 $SCRIPT_PATH --status"
