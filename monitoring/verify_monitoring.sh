#!/bin/bash
# Vérification rapide du système de monitoring

echo "========================================="
echo "Trial Conversion Monitoring - Verification"
echo "========================================="
echo ""

# Check if monitoring script exists
if [ -f "/opt/claude-ceo/workspace/arkwatch/monitoring/trial_conversion_monitor.py" ]; then
    echo "✅ Monitoring script exists"
else
    echo "❌ Monitoring script NOT found"
    exit 1
fi

# Check if script is executable
if [ -x "/opt/claude-ceo/workspace/arkwatch/monitoring/trial_conversion_monitor.py" ]; then
    echo "✅ Script is executable"
else
    echo "⚠️  Script is not executable (run: chmod +x ...)"
fi

# Check monitoring state
if [ -f "/opt/claude-ceo/workspace/arkwatch/monitoring/monitor_state.json" ]; then
    echo "✅ Monitor state file exists"
    CHECKS=$(jq -r '.total_checks' /opt/claude-ceo/workspace/arkwatch/monitoring/monitor_state.json 2>/dev/null)
    ALERTS=$(jq -r '.total_alerts' /opt/claude-ceo/workspace/arkwatch/monitoring/monitor_state.json 2>/dev/null)
    echo "   Total checks: $CHECKS"
    echo "   Total alerts: $ALERTS"
else
    echo "⚠️  Monitor state not found (run monitoring once first)"
fi

# Check alert log
if [ -f "/opt/claude-ceo/workspace/arkwatch/monitoring/alerts.log" ]; then
    ALERT_COUNT=$(wc -l < /opt/claude-ceo/workspace/arkwatch/monitoring/alerts.log)
    echo "✅ Alert log exists ($ALERT_COUNT alerts)"
else
    echo "⚠️  Alert log not found"
fi

# Check cron installation
if crontab -l 2>/dev/null | grep -q "trial_conversion_monitor"; then
    echo "✅ Cron job installed"
    crontab -l | grep trial_conversion_monitor
else
    echo "⚠️  Cron job NOT installed"
    echo "   Run: /opt/claude-ceo/workspace/arkwatch/monitoring/setup_cron.sh"
fi

echo ""
echo "========================================="
echo "Latest Report"
echo "========================================="

# Find latest report
LATEST_REPORT=$(ls -t /opt/claude-ceo/workspace/arkwatch/monitoring/report_*.json 2>/dev/null | head -1)
if [ -n "$LATEST_REPORT" ]; then
    echo "File: $LATEST_REPORT"
    echo ""
    jq -r '"Timestamp: \(.timestamp)\nBugs found: \(.total_bugs_found)\nAlerts: \(.alerts | length)"' "$LATEST_REPORT"

    # Show bug types
    BUGS=$(jq -r '.bugs[].type' "$LATEST_REPORT" 2>/dev/null)
    if [ -n "$BUGS" ]; then
        echo ""
        echo "Bug types:"
        echo "$BUGS" | sed 's/^/  - /'
    fi
else
    echo "No reports found yet"
fi

echo ""
echo "========================================="
echo "Status: OK"
echo "========================================="
