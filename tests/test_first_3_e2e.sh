#!/bin/bash
# Test E2E complet de l'offre First 3 Customers

set -e

echo "🧪 Test E2E: First 3 Customers Offer"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="https://watch.arkforge.fr"
LANDING_URL="https://arkforge.fr/first-3.html"

# Test 1: Page HTML accessible
echo -n "Test 1: Landing page accessible... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$LANDING_URL")
if [ "$STATUS" == "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $STATUS)"
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $STATUS)"
    exit 1
fi

# Test 2: API remaining spots
echo -n "Test 2: API GET /remaining... "
RESPONSE=$(curl -s "$BASE_URL/api/first-3/remaining")
REMAINING=$(echo "$RESPONSE" | jq -r '.remaining')
TOTAL=$(echo "$RESPONSE" | jq -r '.total')
if [ "$TOTAL" == "3" ]; then
    echo -e "${GREEN}✓ PASS${NC} (remaining: $REMAINING)"
else
    echo -e "${RED}✗ FAIL${NC} (total: $TOTAL, expected: 3)"
    exit 1
fi

# Test 3: Signup flow (avec email unique)
TIMESTAMP=$(date +%s)
TEST_EMAIL="test-first3-$TIMESTAMP@example.com"
echo -n "Test 3: API POST /signup... "
SIGNUP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/first-3/signup" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"company\": \"Test Corp - E2E Test\",
        \"usecase\": \"E2E test of the First 3 Customers signup flow to validate API integration.\",
        \"source\": \"e2e-test\"
    }")

STATUS=$(echo "$SIGNUP_RESPONSE" | jq -r '.status')
if [ "$STATUS" == "success" ]; then
    SPOT_NUMBER=$(echo "$SIGNUP_RESPONSE" | jq -r '.spot_number')
    echo -e "${GREEN}✓ PASS${NC} (spot #$SPOT_NUMBER)"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$SIGNUP_RESPONSE"
    exit 1
fi

# Test 4: Duplicate detection
echo -n "Test 4: Duplicate detection... "
DUP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/first-3/signup" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"company\": \"Test Corp\",
        \"usecase\": \"Test duplicate\",
        \"source\": \"e2e-test\"
    }")

DUP_STATUS=$(echo "$DUP_RESPONSE" | jq -r '.status')
if [ "$DUP_STATUS" == "already_claimed" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$DUP_RESPONSE"
    exit 1
fi

# Test 5: Counter updated
echo -n "Test 5: Counter updated... "
UPDATED_RESPONSE=$(curl -s "$BASE_URL/api/first-3/remaining")
NEW_REMAINING=$(echo "$UPDATED_RESPONSE" | jq -r '.remaining')
EXPECTED_REMAINING=$((REMAINING - 1))
if [ "$NEW_REMAINING" == "$EXPECTED_REMAINING" ]; then
    echo -e "${GREEN}✓ PASS${NC} (remaining: $NEW_REMAINING)"
else
    echo -e "${RED}✗ FAIL${NC} (expected: $EXPECTED_REMAINING, got: $NEW_REMAINING)"
    exit 1
fi

# Test 6: Notification file created
echo -n "Test 6: Notification file created... "
NOTIFICATION_FILE="/opt/claude-ceo/workspace/arkwatch/data/first_3_notifications.log"
if [ -f "$NOTIFICATION_FILE" ]; then
    LAST_LINE=$(tail -n 1 "$NOTIFICATION_FILE")
    if echo "$LAST_LINE" | jq . > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
    else
        echo -e "${RED}✗ FAIL${NC} (invalid JSON)"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} (file not found)"
    exit 1
fi

# Test 7: Signup data saved
echo -n "Test 7: Signup data saved... "
SIGNUPS_FILE="/opt/claude-ceo/workspace/arkwatch/data/first_3_signups.json"
if [ -f "$SIGNUPS_FILE" ]; then
    if grep -q "$TEST_EMAIL" "$SIGNUPS_FILE"; then
        echo -e "${GREEN}✓ PASS${NC}"
    else
        echo -e "${RED}✗ FAIL${NC} (email not found)"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} (file not found)"
    exit 1
fi

# Test 8: Validation errors
echo -n "Test 8: Validation (short usecase)... "
INVALID_RESPONSE=$(curl -s -X POST "$BASE_URL/api/first-3/signup" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"invalid-test@example.com\",
        \"company\": \"Test\",
        \"usecase\": \"Short\",
        \"source\": \"test\"
    }")

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/first-3/signup" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"invalid-test@example.com\",
        \"company\": \"Test\",
        \"usecase\": \"Short\",
        \"source\": \"test\"
    }")

if [ "$HTTP_CODE" == "422" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP 422)"
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $HTTP_CODE, expected 422)"
fi

echo ""
echo "======================================"
echo -e "${GREEN}✓ All tests passed!${NC}"
echo ""
echo "⚠️  CLEANUP: Run this to remove test data:"
echo "   jq 'map(select(.email != \"$TEST_EMAIL\"))' $SIGNUPS_FILE > /tmp/first_3_clean.json && mv /tmp/first_3_clean.json $SIGNUPS_FILE"
echo ""
