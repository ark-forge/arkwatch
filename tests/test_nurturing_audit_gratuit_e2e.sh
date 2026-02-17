#!/bin/bash
# E2E Test for Nurturing Audit Gratuit System
# Validates: script execution, cron job, status dashboard, dry-run mode

set -e

echo "========================================="
echo "E2E TEST - Nurturing Audit Gratuit"
echo "========================================="
echo ""

SCRIPT_PATH="/opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py"
CRON_CHECK="nurturing_audit_gratuit"

# Test 1: Script exists and is executable
echo "[1/5] Testing script exists..."
if [ -f "$SCRIPT_PATH" ]; then
    echo "✅ Script found: $SCRIPT_PATH"
else
    echo "❌ Script NOT found: $SCRIPT_PATH"
    exit 1
fi

# Test 2: Cron job is installed
echo ""
echo "[2/5] Testing cron job..."
if crontab -l 2>/dev/null | grep -q "$CRON_CHECK"; then
    echo "✅ Cron job installed"
    crontab -l | grep "$CRON_CHECK"
else
    echo "❌ Cron job NOT installed"
    exit 1
fi

# Test 3: Dry-run mode works
echo ""
echo "[3/5] Testing dry-run mode..."
OUTPUT=$(python3 "$SCRIPT_PATH" --dry-run 2>&1)
if echo "$OUTPUT" | grep -q "ARKWATCH AUDIT GRATUIT NURTURING"; then
    echo "✅ Dry-run mode works"
    echo "$OUTPUT" | grep -E "(Emails due|Results)" | head -5
else
    echo "❌ Dry-run mode failed"
    echo "$OUTPUT"
    exit 1
fi

# Test 4: Status dashboard works
echo ""
echo "[4/5] Testing status dashboard..."
OUTPUT=$(python3 "$SCRIPT_PATH" --status 2>&1)
if echo "$OUTPUT" | grep -q "Total sent"; then
    echo "✅ Status dashboard works"
    echo "$OUTPUT" | grep -E "(Total sent|Total failed|Total leads)" | head -5
else
    echo "❌ Status dashboard failed"
    echo "$OUTPUT"
    exit 1
fi

# Test 5: Documentation exists
echo ""
echo "[5/5] Testing documentation..."
DOCS=(
    "/opt/claude-ceo/workspace/arkwatch/docs/NURTURING_AUDIT_GRATUIT_SYSTEM.md"
    "/opt/claude-ceo/workspace/croissance/QUICKSTART_NURTURING_AUDIT_GRATUIT.md"
    "/opt/claude-ceo/workspace/croissance/DELIVERABLE_TASK_216_NURTURING_AUDIT_GRATUIT.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "✅ Doc found: $(basename $doc)"
    else
        echo "❌ Doc NOT found: $doc"
        exit 1
    fi
done

echo ""
echo "========================================="
echo "✅ ALL TESTS PASSED"
echo "========================================="
echo ""
echo "System is ready for production."
echo ""
echo "Next steps:"
echo "  1. Wait for first audit gratuit lead"
echo "  2. Create Loom video 90s (P1 - URGENT)"
echo "  3. Monitor logs: tail -f /opt/claude-ceo/workspace/arkwatch/logs/nurturing_audit_gratuit.log"
echo ""
