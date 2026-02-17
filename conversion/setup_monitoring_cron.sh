#!/bin/bash
# Setup cron job for real-time conversion monitoring (every 5 minutes)
# GARDIEN TASK #122 - 2026-02-10

SCRIPT_PATH="/opt/claude-ceo/workspace/arkwatch/conversion/monitor_conversion_realtime.py"
LOG_PATH="/opt/claude-ceo/workspace/arkwatch/conversion/monitoring.log"

# Cron entry: every 5 minutes
CRON_ENTRY="*/5 * * * * /usr/bin/python3 $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Add to crontab
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job configured: monitoring every 5 minutes"
echo "📄 Logs: $LOG_PATH"

# Run once now to test
echo ""
echo "🧪 Running initial test..."
/usr/bin/python3 "$SCRIPT_PATH"

echo ""
echo "✅ Setup complete"
