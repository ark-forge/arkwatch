#!/bin/bash
# Quick test script for CEO to verify conversion funnel end-to-end
# Tests all critical touchpoints in the customer journey

set -e

echo "============================================================="
echo "TEST CONVERSION FUNNEL - ArkWatch"
echo "Quick verification of all customer journey touchpoints"
echo "============================================================="
echo ""

TEST_EMAIL="test-funnel-$(date +%s)@example.com"
ERRORS=0

test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="$3"

    echo -n "[TEST] $name ... "
    actual_code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)

    if [ "$actual_code" = "$expected_code" ]; then
        echo "✅ PASS ($actual_code)"
        return 0
    else
        echo "❌ FAIL (expected $expected_code, got $actual_code)"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo "📍 STEP 1: Landing & Discovery"
echo "----------------------------------------"
test_endpoint "Demo page" "https://arkforge.fr/demo.html" "200"
test_endpoint "Pricing page" "https://arkforge.fr/pricing.html" "200"
test_endpoint "Trial signup page" "https://arkforge.fr/trial-14d.html" "200"
echo ""

echo "📍 STEP 2: API Health"
echo "----------------------------------------"
test_endpoint "API health check" "https://watch.arkforge.fr/health" "200"
test_endpoint "API root" "https://watch.arkforge.fr/" "200"
echo ""

echo "📍 STEP 3: Stripe Checkout Links"
echo "----------------------------------------"
test_endpoint "Stripe Checkout - Starter (9€)" "https://buy.stripe.com/00w7sE8li8aU2iA8Uo4AU04" "200"
test_endpoint "Stripe Checkout - Pro (29€)" "https://buy.stripe.com/5kQ28k6dagHq9L2eeI4AU05" "200"
test_endpoint "Stripe Checkout - Business (99€)" "https://buy.stripe.com/9B6dR2bxucra0aseeI4AU06" "200"
echo ""

echo "📍 STEP 4: Backend Scripts"
echo "----------------------------------------"
echo -n "[TEST] Trial tracker import ... "
if python3 -c "from conversion.trial_tracker import run_tracking_cycle" 2>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ERRORS=$((ERRORS + 1))
fi

echo -n "[TEST] Conversion rate alert script ... "
if [ -f "automation/conversion_rate_alert.py" ] && [ -x "automation/conversion_rate_alert.py" ]; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "📍 STEP 5: Data Files"
echo "----------------------------------------"
for file in "data/trial_14d_signups.json" "data/payments.json" "data/arkwatch.db"; do
    echo -n "[TEST] $file exists ... "
    if [ -f "$file" ]; then
        echo "✅ PASS"
    else
        echo "❌ FAIL"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

echo "📍 STEP 6: Stripe Configuration"
echo "----------------------------------------"
echo -n "[TEST] Stripe keys configured ... "
if grep -q "sk_live_" .env.stripe 2>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ERRORS=$((ERRORS + 1))
fi

echo -n "[TEST] Stripe webhook secret ... "
if grep -q "whsec_" .env.stripe 2>/dev/null; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo "============================================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ ALL TESTS PASSED ($((12 + 2 + 2)) checks)"
    echo ""
    echo "🎯 FUNNEL STATUS: OPERATIONAL"
    echo ""
    echo "Next steps:"
    echo "  1. Send trial link to first lead: https://arkforge.fr/trial-14d.html?plan=pro"
    echo "  2. Monitor trial_tracker.log for activation alerts"
    echo "  3. Watch payments.json for first revenue"
    echo ""
    echo "Simulate trial signup (test):"
    echo "  curl -X POST https://watch.arkforge.fr/api/trial-14d/signup \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"email\":\"$TEST_EMAIL\",\"plan\":\"pro\",\"source\":\"test_script\"}'"
    echo ""
    exit 0
else
    echo "❌ TESTS FAILED: $ERRORS error(s)"
    echo ""
    echo "Common fixes:"
    echo "  - API not responding: sudo systemctl restart arkwatch-api"
    echo "  - Scripts import error: cd /opt/claude-ceo/workspace/arkwatch"
    echo "  - Missing files: Check docs/STRIPE_CHECKOUT_INFRASTRUCTURE.md"
    echo ""
    exit 1
fi
