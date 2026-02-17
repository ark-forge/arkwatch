#!/bin/bash
# Setup cron job for trial conversion monitoring (every 5 minutes)

SCRIPT_PATH="/opt/claude-ceo/workspace/arkwatch/monitoring/trial_conversion_monitor.py"
CRON_LOG="/opt/claude-ceo/workspace/arkwatch/logs/trial_monitor_cron.log"

# Ensure log directory exists
mkdir -p "$(dirname "$CRON_LOG")"

# Add cron job (every 5 minutes)
CRON_ENTRY="*/5 * * * * /usr/bin/python3 $SCRIPT_PATH >> $CRON_LOG 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "✅ Cron job already exists for trial conversion monitor"
    exit 0
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job added successfully"
    echo "   Script: $SCRIPT_PATH"
    echo "   Schedule: Every 5 minutes"
    echo "   Log: $CRON_LOG"
    echo ""
    echo "Verify with: crontab -l | grep trial_conversion_monitor"
else
    echo "❌ Failed to add cron job"
    exit 1
fi
