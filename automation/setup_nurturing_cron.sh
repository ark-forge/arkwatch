#!/bin/bash
# Setup cron job for ArkWatch nurturing email sequence
# Runs every hour to check for due nurturing emails

SCRIPT="/opt/claude-ceo/workspace/arkwatch/automation/nurturing_sequence.py"
LOG="/opt/claude-ceo/workspace/arkwatch/logs/nurturing.log"
CRON_CMD="0 * * * * /usr/bin/python3 $SCRIPT >> $LOG 2>&1"

# Create log directory
mkdir -p /opt/claude-ceo/workspace/arkwatch/logs

# Check if cron already exists
if crontab -l 2>/dev/null | grep -q "nurturing_sequence.py"; then
    echo "Nurturing cron already installed."
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "Nurturing cron installed: runs every hour."
fi

echo "Current crontab:"
crontab -l 2>/dev/null | grep nurturing || echo "  (none)"
echo ""
echo "To test manually: python3 $SCRIPT --dry-run"
echo "To check status:  python3 $SCRIPT --status"
