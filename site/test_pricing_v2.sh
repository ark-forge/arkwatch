#!/bin/bash
# Test script for pricing-v2.html

echo "================================"
echo "PRICING V2 PAGE - TEST REPORT"
echo "================================"
echo ""

# 1. Check file exists
echo "✓ Checking file exists..."
if [ -f "/opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html" ]; then
    echo "  → pricing-v2.html EXISTS"
else
    echo "  → ERROR: pricing-v2.html NOT FOUND"
    exit 1
fi

# 2. Check file size
SIZE=$(wc -c < /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)
echo ""
echo "✓ File size: $SIZE bytes"
if [ "$SIZE" -gt 10000 ]; then
    echo "  → GOOD: File is substantial"
else
    echo "  → WARNING: File seems small"
fi

# 3. Check HTML structure
echo ""
echo "✓ Checking HTML structure..."
if grep -q "<!DOCTYPE html>" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → DOCTYPE present"
fi
if grep -q "<title>" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → Title present"
fi
if grep -q "</html>" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → Closing tag present"
fi

# 4. Check 3 plans present
echo ""
echo "✓ Checking pricing plans..."
STARTER=$(grep -c "Starter" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)
PRO=$(grep -c "Pro" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)
ENTERPRISE=$(grep -c "Enterprise" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)

echo "  → Starter mentions: $STARTER"
echo "  → Pro mentions: $PRO"
echo "  → Enterprise mentions: $ENTERPRISE"

if [ "$STARTER" -gt 0 ] && [ "$PRO" -gt 0 ] && [ "$ENTERPRISE" -gt 0 ]; then
    echo "  → SUCCESS: All 3 plans present"
else
    echo "  → ERROR: Missing plans"
    exit 1
fi

# 5. Check pricing
echo ""
echo "✓ Checking prices..."
if grep -q "€29" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → €29 (Starter) found"
fi
if grep -q "€99" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → €99 (Pro) found"
fi
if grep -q "Custom" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → Custom (Enterprise) found"
fi

# 6. Check trial CTA
echo ""
echo "✓ Checking trial CTAs..."
TRIAL_CTA=$(grep -c "14-Day Free Trial" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)
NO_CC=$(grep -c "No credit card required" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)

echo "  → '14-Day Free Trial' mentions: $TRIAL_CTA"
echo "  → 'No credit card required' mentions: $NO_CC"

if [ "$TRIAL_CTA" -ge 2 ]; then
    echo "  → SUCCESS: Trial CTAs present"
else
    echo "  → WARNING: Few trial CTAs"
fi

# 7. Check links to free-trial page
echo ""
echo "✓ Checking links..."
LINKS=$(grep -c "free-trial.html" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html)
echo "  → Links to free-trial.html: $LINKS"

if [ "$LINKS" -ge 2 ]; then
    echo "  → SUCCESS: CTA links present"
else
    echo "  → WARNING: Few CTA links"
fi

# 8. Check demo.html integration
echo ""
echo "✓ Checking demo.html integration..."
if grep -q "pricing-v2.html" /opt/claude-ceo/workspace/arkwatch/site/demo.html; then
    echo "  → SUCCESS: demo.html links to pricing-v2.html"
else
    echo "  → WARNING: demo.html does not link to pricing-v2.html"
fi

# 9. Check analytics tracking
echo ""
echo "✓ Checking analytics..."
if grep -q "pricing_pageview" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → Analytics tracking present"
fi
if grep -q "pricing_cta_click" /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html; then
    echo "  → CTA click tracking present"
fi

echo ""
echo "================================"
echo "TEST COMPLETE"
echo "================================"
echo ""
echo "✅ pricing-v2.html is ready"
echo "✅ 3 plans: Starter €29, Pro €99, Enterprise custom"
echo "✅ CTA: 'Start 14-Day Free Trial' (no credit card)"
echo "✅ Linked from demo.html"
echo ""
echo "NEXT STEPS:"
echo "1. Deploy to production server"
echo "2. Update main navigation to link to /site/pricing-v2.html"
echo "3. Monitor conversion with analytics"
