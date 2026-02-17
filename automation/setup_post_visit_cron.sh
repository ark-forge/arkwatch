#!/bin/bash
# Setup cron for email J+0 post-visit automation
# Runs every 30 minutes to catch visitors who left 2+ hours ago

SCRIPT="/opt/claude-ceo/workspace/arkwatch/automation/email_j0_post_visit.py"
LOG="/opt/claude-ceo/workspace/arkwatch/logs/post_visit_email.log"
CRON_LINE="*/30 * * * * /usr/bin/python3 $SCRIPT >> $LOG 2>&1"

# Create logs directory
mkdir -p /opt/claude-ceo/workspace/arkwatch/logs

# Check if cron already exists
if crontab -l 2>/dev/null | grep -q "email_j0_post_visit"; then
    echo "Cron already exists for post-visit email automation"
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Cron installed: $CRON_LINE"
fi

echo "Done. Check with: crontab -l | grep post_visit"
