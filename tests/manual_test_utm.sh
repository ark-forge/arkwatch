#!/bin/bash
# Manual test script for UTM tracking

API_URL="http://127.0.0.1:8080"

echo "=== Testing Conversion Tracking ==="
echo ""

# Generate random email for testing
RANDOM_EMAIL="test_$(date +%s)@example.com"

# Test 1: Signup WITHOUT ref parameter (should default to "direct")
echo "Test 1: Signup without ?ref= parameter"
curl -s -X POST "${API_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${RANDOM_EMAIL}\",
    \"name\": \"Test Direct User\",
    \"privacy_accepted\": true
  }" | jq -r '.message'
echo ""

# Wait a bit
sleep 1

# Test 2: Signup WITH ref=devto parameter
RANDOM_EMAIL_2="test_devto_$(date +%s)@example.com"
echo "Test 2: Signup with ?ref=devto parameter"
curl -s -X POST "${API_URL}/api/v1/auth/register?ref=devto" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${RANDOM_EMAIL_2}\",
    \"name\": \"Test DevTo User\",
    \"privacy_accepted\": true
  }" | jq -r '.message'
echo ""

# Wait a bit
sleep 1

# Test 3: Signup WITH ref=ph (ProductHunt) parameter
RANDOM_EMAIL_3="test_ph_$(date +%s)@example.com"
echo "Test 3: Signup with ?ref=ph parameter"
curl -s -X POST "${API_URL}/api/v1/auth/register?ref=ph" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${RANDOM_EMAIL_3}\",
    \"name\": \"Test ProductHunt User\",
    \"privacy_accepted\": true
  }" | jq -r '.message'
echo ""

echo "=== Verification ==="
echo "Check api_keys.json to verify signup_source field:"
echo ""
echo "Last 3 signups:"
jq -r '.[] | {email: .email, source: .signup_source, created_at: .created_at}' \
  /opt/claude-ceo/workspace/arkwatch/data/api_keys.json | tail -30
echo ""

echo "✅ Manual test complete!"
echo ""
echo "To test stats endpoints, you need an admin API key:"
echo "  curl -X GET \"${API_URL}/api/stats\" -H \"X-API-Key: YOUR_ADMIN_KEY\""
