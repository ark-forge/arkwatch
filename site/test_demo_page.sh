#!/bin/bash
# Test script for interactive demo page

echo "🧪 Testing ArkWatch Demo Page"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test 1: Check if demo.html exists
echo -n "Test 1: Demo page file exists... "
if [ -f "/opt/claude-ceo/workspace/arkwatch/site/demo.html" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 2: Check HTML structure
echo -n "Test 2: HTML has required structure... "
if grep -q "id=\"emailGate\"" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "id=\"step3\"" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "class=\"terminal\"" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 3: Check API endpoint configuration
echo -n "Test 3: API endpoint configured... "
if grep -q "/api/demo-leads" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 4: Check redirect configuration
echo -n "Test 4: Auto-redirect to trial configured... "
if grep -q "trial-14d.html?from=demo" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "setTimeout" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 5: Check backend endpoint exists
echo -n "Test 5: Backend API endpoint exists... "
if grep -q "@router.post(\"/api/demo-leads\")" "/opt/claude-ceo/workspace/arkwatch/src/api/routers/leadgen_analytics.py"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 6: Check terminal demo content
echo -n "Test 6: Terminal demo steps present... "
STEP_COUNT=$(grep -c "class=\"step\"" "/opt/claude-ceo/workspace/arkwatch/site/demo.html")
if [ "$STEP_COUNT" -ge 5 ]; then
    echo -e "${GREEN}✓ PASS${NC} (Found $STEP_COUNT steps)"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC} (Found only $STEP_COUNT steps, expected 5)"
    FAILED=$((FAILED+1))
fi

# Test 7: Check email gate with benefits
echo -n "Test 7: Email gate with benefits list... "
if grep -q "benefits-list" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "Unlock Full Demo" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 8: Check locked content blur
echo -n "Test 8: Locked content blur effect... "
if grep -q "classList.add('locked')" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "filter: blur" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 9: Check CTA section
echo -n "Test 9: CTA section with trial link... "
if grep -q "cta-section" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "Start Free Trial" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

# Test 10: Check analytics tracking
echo -n "Test 10: Analytics tracking configured... "
if grep -q "gtag" "/opt/claude-ceo/workspace/arkwatch/site/demo.html" && \
   grep -q "demo_unlock" "/opt/claude-ceo/workspace/arkwatch/site/demo.html"; then
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED=$((FAILED+1))
fi

echo ""
echo "================================"
echo "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Deploy demo.html to production"
    echo "2. Test API endpoint: POST /api/demo-leads"
    echo "3. Verify email capture in /opt/claude-ceo/workspace/arkwatch/data/demo_leads.json"
    echo "4. Add link to demo page from landing page"
    echo "5. Track conversion rate (target: 10%)"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please fix before deploying.${NC}"
    exit 1
fi
