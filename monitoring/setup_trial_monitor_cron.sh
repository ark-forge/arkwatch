#!/bin/bash
# Setup cron job for trial monitoring every 5 minutes
# GARDIEN TASK #20261124

SCRIPT_DIR="/opt/claude-ceo/workspace/arkwatch/monitoring"
MONITOR_SCRIPT="$SCRIPT_DIR/trial_realtime_monitor.py"
CRON_LOG="/opt/claude-ceo/workspace/arkwatch/monitoring/trial_monitor_cron.log"

# Create cron job entry
CRON_CMD="*/5 * * * * cd $SCRIPT_DIR && /usr/bin/python3 $MONITOR_SCRIPT >> $CRON_LOG 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$MONITOR_SCRIPT"; then
    echo "✓ Cron job already exists for trial monitoring"
    echo "Current cron:"
    crontab -l | grep "$MONITOR_SCRIPT"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Cron job added: monitoring every 5 minutes"
    echo "$CRON_CMD"
fi

echo ""
echo "Monitoring setup complete:"
echo "  Script: $MONITOR_SCRIPT"
echo "  Frequency: Every 5 minutes"
echo "  Log: $CRON_LOG"
echo "  Reports: /opt/claude-ceo/workspace/gardien/RAPPORT_BUGS_TRIAL_14D_*.md"
echo ""
echo "To check cron status:"
echo "  crontab -l | grep trial_realtime_monitor"
echo ""
echo "To view logs:"
echo "  tail -f $CRON_LOG"
