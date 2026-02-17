#!/bin/bash
# Setup cron job for automated trial follow-up system
# Runs every 6 hours: 00:00, 06:00, 12:00, 18:00

CRON_JOB="0 */6 * * * cd /opt/claude-ceo/workspace/arkwatch/conversion && /usr/bin/python3 automated_trial_followup.py >> /opt/claude-ceo/workspace/arkwatch/logs/trial_followup_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -F "automated_trial_followup.py" > /dev/null; then
    echo "✅ Cron job already exists"
    echo "Current crontab:"
    crontab -l | grep "automated_trial_followup.py"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job added successfully"
    echo "Schedule: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)"
fi

# Create log directory
mkdir -p /opt/claude-ceo/workspace/arkwatch/logs

# Show next execution times
echo ""
echo "📅 Next 3 execution times:"
echo "$(date -d '00:00 today' '+%Y-%m-%d %H:%M UTC')"
echo "$(date -d '06:00 today' '+%Y-%m-%d %H:%M UTC')"
echo "$(date -d '12:00 today' '+%Y-%m-%d %H:%M UTC')"
echo "$(date -d '18:00 today' '+%Y-%m-%d %H:%M UTC')"

echo ""
echo "✅ Setup complete!"
echo "View logs: tail -f /opt/claude-ceo/workspace/arkwatch/logs/trial_followup_cron.log"
