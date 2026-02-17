#!/bin/bash
# Setup cron for aggressive trial conversion sequence
# Runs every 6 hours to check delays and send next steps
# Step 1 -> immediate, Step 2 -> 24h after, Step 3 -> 48h after

SCRIPT="/opt/claude-ceo/workspace/arkwatch/automation/aggressive_trial_conversion.py"
LOG="/opt/claude-ceo/workspace/arkwatch/logs/aggressive_conversion.log"

# Create log directory
mkdir -p "$(dirname "$LOG")"

# Check if cron already exists
if crontab -l 2>/dev/null | grep -q "aggressive_trial_conversion"; then
    echo "Cron already configured. Updating..."
    crontab -l 2>/dev/null | grep -v "aggressive_trial_conversion" | crontab -
fi

# Add cron: every 6 hours at :15 to avoid conflicts
(crontab -l 2>/dev/null; echo "15 */6 * * * cd /opt/claude-ceo && python3 $SCRIPT --max-emails 10 >> $LOG 2>&1") | crontab -

echo "Cron configured:"
crontab -l | grep aggressive
echo ""
echo "To run manually: python3 $SCRIPT --dry-run"
echo "To check status: python3 $SCRIPT --status"
echo "Logs: $LOG"
