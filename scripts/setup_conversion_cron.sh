#!/bin/bash
# Setup cron jobs for automated conversion monitoring
# Run this script once to install all monitoring tasks

set -e

echo "============================================================="
echo "SETUP CONVERSION MONITORING - Cron Jobs"
echo "============================================================="

# Backup existing crontab
echo "[1/3] Backing up current crontab..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

# Create new crontab entries (append to existing)
CRON_ENTRIES="
# ArkWatch Conversion Monitoring
# Trial tracker: Check for activations and conversions every 10 minutes
*/10 * * * * cd /opt/claude-ceo/workspace/arkwatch && python3 conversion/trial_tracker.py >> /opt/claude-ceo/logs/trial_tracker.log 2>&1

# Trial leads monitor: Check for new leads every 30 minutes
*/30 * * * * cd /opt/claude-ceo/workspace/arkwatch && python3 automation/trial_leads_monitor.py >> /opt/claude-ceo/logs/trial_leads_monitor.log 2>&1

# Conversion rate alert: Daily check at 09:00 UTC
0 9 * * * cd /opt/claude-ceo/workspace/arkwatch && python3 automation/conversion_rate_alert.py >> /opt/claude-ceo/logs/conversion_rate_alert.log 2>&1
"

echo "[2/3] Installing cron jobs..."

# Check if entries already exist
if crontab -l 2>/dev/null | grep -q "ArkWatch Conversion Monitoring"; then
    echo "  ⚠️  Cron jobs already installed - skipping"
else
    (crontab -l 2>/dev/null || true; echo "$CRON_ENTRIES") | crontab -
    echo "  ✅ Cron jobs installed"
fi

echo "[3/3] Creating log directory..."
mkdir -p /opt/claude-ceo/logs
chmod 755 /opt/claude-ceo/logs

echo ""
echo "============================================================="
echo "✅ SETUP COMPLETE"
echo "============================================================="
echo ""
echo "📊 INSTALLED CRON JOBS:"
echo "  1. Trial tracker: Every 10 minutes"
echo "  2. Trial leads monitor: Every 30 minutes"
echo "  3. Conversion rate alert: Daily at 09:00 UTC"
echo ""
echo "📁 LOGS:"
echo "  → /opt/claude-ceo/logs/trial_tracker.log"
echo "  → /opt/claude-ceo/logs/trial_leads_monitor.log"
echo "  → /opt/claude-ceo/logs/conversion_rate_alert.log"
echo ""
echo "🔧 VERIFY:"
echo "  crontab -l | grep ArkWatch"
echo ""
echo "🗑️  UNINSTALL:"
echo "  crontab -e  # Remove lines containing 'ArkWatch Conversion Monitoring'"
echo "============================================================="
