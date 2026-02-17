#!/bin/bash
#
# Setup cron job for free_trial_nurture.py
#
# Usage: sudo bash automation/setup_cron.sh

SCRIPT_PATH="/opt/claude-ceo/workspace/arkwatch/automation/free_trial_nurture.py"
CRON_LINE="0 10 * * * cd /opt/claude-ceo/workspace/arkwatch && python3 ${SCRIPT_PATH} >> /opt/claude-ceo/workspace/arkwatch/logs/nurture_cron.log 2>&1"

echo "=== Setting up cron job for Free Trial Nurture ==="
echo ""
echo "Script: ${SCRIPT_PATH}"
echo "Schedule: Daily at 10:00 UTC"
echo ""

# Check if cron line already exists
if crontab -l 2>/dev/null | grep -F "${SCRIPT_PATH}" > /dev/null; then
    echo "✓ Cron job already exists"
    echo ""
    echo "Current cron line:"
    crontab -l | grep -F "${SCRIPT_PATH}"
    echo ""
    echo "To remove: crontab -e"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "${CRON_LINE}") | crontab -

    if [ $? -eq 0 ]; then
        echo "✓ Cron job added successfully"
        echo ""
        echo "Cron line:"
        echo "${CRON_LINE}"
        echo ""
        echo "To verify: crontab -l"
        echo "To edit: crontab -e"
        echo "To remove: crontab -e (then delete the line)"
    else
        echo "✗ Failed to add cron job"
        exit 1
    fi
fi

echo ""
echo "=== Setup complete ==="
