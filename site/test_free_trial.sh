#!/bin/bash
# Test de non-régression pour /free-trial
# Usage: ./test_free_trial.sh

echo "=== TEST FREE-TRIAL PAGE ==="
echo ""

# Test 1: Page accessible
echo "1. Page accessible..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://arkforge.fr/free-trial.html)
if [ "$STATUS" = "200" ]; then
  echo "   ✅ OK (200)"
else
  echo "   ❌ FAIL ($STATUS)"
  exit 1
fi

# Test 2: Contenu principal présent
echo "2. Contenu principal..."
CONTENT=$(curl -s https://arkforge.fr/free-trial.html | grep -c "6 Months FREE")
if [ "$CONTENT" -gt 0 ]; then
  echo "   ✅ OK (contenu détecté)"
else
  echo "   ❌ FAIL (contenu manquant)"
  exit 1
fi

# Test 3: Formulaire présent
echo "3. Formulaire signup..."
FORM=$(curl -s https://arkforge.fr/free-trial.html | grep -c "api/early-signup")
if [ "$FORM" -gt 0 ]; then
  echo "   ✅ OK (formulaire présent)"
else
  echo "   ❌ FAIL (formulaire manquant)"
  exit 1
fi

# Test 4: API spots
echo "4. API /api/free-trial/spots..."
SPOTS=$(curl -s https://watch.arkforge.fr/api/free-trial/spots | grep -c "remaining")
if [ "$SPOTS" -gt 0 ]; then
  echo "   ✅ OK (API répond)"
else
  echo "   ❌ FAIL (API ne répond pas)"
  exit 1
fi

# Test 5: Redirection corrigée (dashboard.html)
echo "5. Redirection dashboard..."
REDIRECT=$(curl -s https://arkforge.fr/free-trial.html | grep -c "dashboard.html")
if [ "$REDIRECT" -gt 0 ]; then
  echo "   ✅ OK (redirection corrigée)"
else
  echo "   ❌ FAIL (redirection incorrecte)"
  exit 1
fi

echo ""
echo "=== TOUS LES TESTS PASSENT ✅ ==="
echo ""
echo "Détails:"
curl -s https://watch.arkforge.fr/api/free-trial/spots | jq '.'
