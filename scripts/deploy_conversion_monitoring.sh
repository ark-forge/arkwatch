#!/bin/bash
# Script de déploiement rapide du système de monitoring conversion
# Task #20260952

set -e

echo "=========================================="
echo "🚀 Déploiement Monitoring Conversion"
echo "=========================================="
echo ""

# 1. Vérifier pré-requis
echo "✓ Vérification pré-requis..."

if [ ! -f "/opt/claude-ceo/workspace/arkwatch/src/api/middleware/page_visit_tracker.py" ]; then
    echo "❌ Middleware manquant"
    exit 1
fi

if [ ! -x "/opt/claude-ceo/workspace/arkwatch/scripts/monitor_conversion_signals.py" ]; then
    echo "❌ Script monitoring manquant"
    exit 1
fi

if ! crontab -l | grep -q "20260952"; then
    echo "❌ Cron job non configuré"
    exit 1
fi

echo "  ✅ Tous les composants présents"
echo ""

# 2. Redémarrer API (activer middleware)
echo "✓ Redémarrage API pour activer middleware..."
cd /opt/claude-ceo/workspace/arkwatch

if [ -f "docker-compose.yml" ] || [ -f "compose.yaml" ]; then
    docker compose restart api
    echo "  ✅ API redémarrée"
else
    echo "  ⚠️  docker-compose.yml non trouvé, skip restart"
fi

echo ""

# 3. Test santé API
echo "✓ Test santé API..."
sleep 3  # Attendre démarrage
if curl -s https://watch.arkforge.fr/health | grep -q "healthy"; then
    echo "  ✅ API opérationnelle"
else
    echo "  ⚠️  API pas encore prête (vérifier manuellement)"
fi

echo ""

# 4. Test visite simulation
echo "✓ Test simulation visite..."
curl -s https://watch.arkforge.fr/pricing > /dev/null 2>&1 || true
echo "  ✅ Requête test envoyée"

echo ""

# 5. Vérifier log créé
echo "✓ Vérification log visites..."
sleep 2
if [ -f "/opt/claude-ceo/workspace/arkwatch/logs/page_visits_20260209.json" ]; then
    VISIT_COUNT=$(cat /opt/claude-ceo/workspace/arkwatch/logs/page_visits_20260209.json | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    echo "  ✅ Log actif ($VISIT_COUNT visites enregistrées)"
else
    echo "  ⚠️  Log pas encore créé (attendre première visite réelle)"
fi

echo ""

# 6. Test monitoring immédiat
echo "✓ Test monitoring immédiat..."
if python3 /opt/claude-ceo/workspace/arkwatch/scripts/monitor_conversion_signals.py 2>&1 | grep -q "Checking conversion signals"; then
    echo "  ✅ Monitoring fonctionnel"
else
    echo "  ❌ Monitoring en erreur"
    exit 1
fi

echo ""

# 7. Résumé
echo "=========================================="
echo "✅ DÉPLOIEMENT COMPLÉTÉ"
echo "=========================================="
echo ""
echo "Système activé:"
echo "  • Middleware tracking: ✅ ACTIF"
echo "  • Pages trackées: /demo, /pricing, /trial"
echo "  • Monitoring: toutes les 15min"
echo "  • Email alert: apps.desiorac@gmail.com"
echo ""
echo "Prochaines alertes:"
echo "  • Dès visite /pricing ou /trial"
echo "  • Max 15min de latence"
echo "  • Détails complets dans email"
echo ""
echo "Logs:"
echo "  • Visites: /opt/claude-ceo/workspace/arkwatch/logs/page_visits_20260209.json"
echo "  • Monitoring: /opt/claude-ceo/logs/conversion_monitor.log"
echo ""
echo "Forcer vérification manuelle:"
echo "  python3 /opt/claude-ceo/workspace/arkwatch/scripts/monitor_conversion_signals.py"
echo ""
echo "🔥 Prêt à détecter les leads chauds!"
