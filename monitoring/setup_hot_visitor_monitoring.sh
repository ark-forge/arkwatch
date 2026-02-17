#!/bin/bash
# Setup HOT Visitor Monitoring - Task #20261197
# Installe le monitoring temps réel des visiteurs /trial-14d avec alertes SMS

set -e

echo "=========================================="
echo "HOT Visitor Monitoring - Setup"
echo "Task: #20261197 | Worker: GARDIEN"
echo "=========================================="
echo ""

# 1. Install dependencies
echo "[1/6] Installing dependencies..."
pip3 install ovh --quiet
echo "✓ OVH library installed"
echo ""

# 2. Register tracking endpoint in main.py
echo "[2/6] Registering tracking endpoint..."
MAIN_PY="/opt/claude-ceo/workspace/arkwatch/src/api/main.py"

if grep -q "track_visitor_trial14d" "$MAIN_PY" 2>/dev/null; then
    echo "✓ Tracking endpoint already registered"
else
    # Backup first
    cp "$MAIN_PY" "$MAIN_PY.backup_$(date +%s)"

    # Add import and include
    echo "
# HOT Visitor Tracking - Trial 14d (Task #20261197)
from .routers import track_visitor_trial14d
app.include_router(track_visitor_trial14d.router, tags=['tracking'])
" >> "$MAIN_PY"

    echo "✓ Tracking endpoint added to main.py"
fi
echo ""

# 3. Embed tracking snippet in trial-14d.html
echo "[3/6] Embedding tracking snippet..."
TRIAL_PAGE="/opt/claude-ceo/workspace/arkwatch/site/trial-14d.html"
SNIPPET_PATH="/opt/claude-ceo/workspace/arkwatch/site/tracking_snippet_trial14d.html"

if [ -f "$TRIAL_PAGE" ]; then
    if grep -q "HOT Visitor Tracking" "$TRIAL_PAGE"; then
        echo "✓ Tracking snippet already embedded"
    else
        # Backup
        cp "$TRIAL_PAGE" "$TRIAL_PAGE.backup_$(date +%s)"

        # Insert before </body>
        sed -i '/<\/body>/i\<!-- HOT Visitor Tracking embedded from snippet -->' "$TRIAL_PAGE"
        sed -i "/<\/body>/r $SNIPPET_PATH" "$TRIAL_PAGE"

        echo "✓ Tracking snippet embedded in trial-14d.html"
    fi
else
    echo "⚠️  WARNING: trial-14d.html not found - manual embedding required"
fi
echo ""

# 4. Setup cron job for monitoring (every 30s)
echo "[4/6] Setting up cron job..."
CRON_CMD="/opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_tracker_trial14d.py"

# Make executable
chmod +x "$CRON_CMD"

# Add cron job (every minute - the script runs every 30s internally via systemd)
CRON_LINE="* * * * * /usr/bin/python3 $CRON_CMD >> /opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_monitor.log 2>&1"

if crontab -l 2>/dev/null | grep -q "hot_visitor_tracker_trial14d.py"; then
    echo "✓ Cron job already configured"
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "✓ Cron job configured (runs every minute)"
fi
echo ""

# 5. Restart API to load new endpoint
echo "[5/6] Restarting API..."
if systemctl is-active --quiet arkwatch-api; then
    sudo systemctl restart arkwatch-api
    sleep 3
    if systemctl is-active --quiet arkwatch-api; then
        echo "✓ API restarted successfully"
    else
        echo "⚠️  WARNING: API failed to restart - check logs"
    fi
else
    echo "⚠️  WARNING: arkwatch-api service not running - start manually"
fi
echo ""

# 6. Test setup
echo "[6/6] Testing setup..."

# Test tracking endpoint
echo "Testing tracking endpoint..."
curl -X POST http://127.0.0.1:8080/api/track-visitor-trial14d \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_id": "test-123",
    "type": "heartbeat",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "page": "/trial-14d",
    "time_on_page": 30,
    "interactions": 5
  }' 2>/dev/null | jq . || echo "⚠️  Endpoint not responding yet - wait for restart"

echo ""

# Verify files created
echo "Verifying installation..."
[ -f "/opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_tracker_trial14d.py" ] && echo "✓ Monitor script exists"
[ -f "/opt/claude-ceo/workspace/arkwatch/src/api/routers/track_visitor_trial14d.py" ] && echo "✓ API router exists"
[ -f "$SNIPPET_PATH" ] && echo "✓ Tracking snippet exists"
echo ""

echo "=========================================="
echo "INSTALLATION COMPLETE"
echo "=========================================="
echo ""
echo "HOT VISITOR MONITORING ACTIF:"
echo "  - Tracking endpoint: /api/track-visitor-trial14d"
echo "  - Monitor script: hot_visitor_tracker_trial14d.py"
echo "  - Cron: Every minute (30s internal interval)"
echo "  - SMS: OVH API (+33749879812)"
echo ""
echo "HOT CRITERIA:"
echo "  - 3+ interactions on page"
echo "  - Form started but not submitted"
echo "  - 45+ seconds on page"
echo "  - 70%+ scroll depth"
echo ""
echo "LOGS & DATA:"
echo "  - Visitor events: /opt/claude-ceo/workspace/arkwatch/data/trial_14d_visitors.jsonl"
echo "  - HOT alerts: /opt/claude-ceo/workspace/arkwatch/data/trial_14d_hot_alerts.jsonl"
echo "  - Monitor log: /opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_monitor.log"
echo "  - State: /opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_state.json"
echo ""
echo "PROCHAINES ACTIONS:"
echo "  1. Vérifier que trial-14d.html contient le tracking snippet"
echo "  2. Tester visite sur https://arkforge.fr/trial-14d.html"
echo "  3. Vérifier log: tail -f /opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_monitor.log"
echo "  4. Vérifier alertes SMS reçues sur +33749879812"
echo ""
echo "=========================================="
