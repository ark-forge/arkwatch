#!/bin/bash
# Setup cron job for HOT SIGNAL RELANCE automation
# Runs every 5 minutes to detect hot page visits and send contextual emails
# FONDATIONS TASK #282 - 2026-02-11

SCRIPT="/opt/claude-ceo/workspace/arkwatch/automation/hot_signal_relance.py"
LOG="/opt/claude-ceo/workspace/arkwatch/data/hot_signal_relance_cron.log"
CRON_JOB="*/5 * * * * /usr/bin/python3 $SCRIPT >> $LOG 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "hot_signal_relance.py"; then
    echo "Cron job already exists for hot_signal_relance.py"
    crontab -l | grep "hot_signal_relance"
    exit 0
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✓ Cron job installed: every 5 minutes"
echo "  Script: $SCRIPT"
echo "  Log: $LOG"
echo ""
echo "Verify with: crontab -l | grep hot_signal"
