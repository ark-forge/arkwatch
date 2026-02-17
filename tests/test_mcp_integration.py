#!/usr/bin/env python3
"""Test d'intégration pour le flux MCP EU AI Act"""

import os
import sys

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv("/opt/claude-ceo/workspace/arkwatch/.env.stripe")

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_mcp_info_endpoint():
    """Test de l'endpoint d'information produit"""
    print("\n🧪 Test 1: GET /api/checkout/mcp-eu-ai-act/info")
    response = client.get("/api/checkout/mcp-eu-ai-act/info")

    print(f"   Status: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"   Product: {data['product']}")
    print(f"   Price: {data['price']['amount']}€/{data['price']['interval']}")
    print(f"   Trial: {data['price']['trial_days']} days")
    print(f"   Features: {len(data['features'])} features")

    assert data["product"] == "MCP EU AI Act Compliance Monitoring"
    assert data["price"]["amount"] == 9
    assert data["price"]["currency"] == "EUR"
    print("   ✅ Test passed!")


def test_stripe_price_env_var():
    """Test que la variable d'environnement Stripe est bien définie"""
    print("\n🧪 Test 2: Variable d'environnement STRIPE_PRICE_MCP_EU_AI_ACT")

    price_id = os.getenv("STRIPE_PRICE_MCP_EU_AI_ACT")
    print(f"   Price ID: {price_id}")

    assert price_id is not None, "STRIPE_PRICE_MCP_EU_AI_ACT doit être défini"
    assert price_id.startswith("price_"), "Le Price ID doit commencer par 'price_'"
    print("   ✅ Test passed!")


def test_checkout_endpoint_validation():
    """Test de la validation de l'endpoint checkout"""
    print("\n🧪 Test 3: Validation de l'endpoint checkout")

    # Test avec un email invalide
    print("   - Test email invalide...")
    response = client.post(
        "/api/checkout/mcp-eu-ai-act",
        json={
            "email": "invalid-email",
            "trial_days": 14
        }
    )
    assert response.status_code == 422
    print("     ✅ Validation email fonctionne!")

    # Test avec des données manquantes
    print("   - Test données manquantes...")
    response = client.post(
        "/api/checkout/mcp-eu-ai-act",
        json={}
    )
    assert response.status_code == 422
    print("     ✅ Validation champs requis fonctionne!")


def test_api_routes():
    """Test que toutes les routes nécessaires sont chargées"""
    print("\n🧪 Test 4: Routes de l'API")

    # Récupérer toutes les routes
    routes = [route.path for route in app.routes]

    # Vérifier que nos routes sont présentes
    assert "/api/checkout/mcp-eu-ai-act" in routes
    assert "/api/checkout/mcp-eu-ai-act/info" in routes
    print("   ✅ Toutes les routes sont chargées!")


def test_landing_page_exists():
    """Test que la landing page MCP existe"""
    print("\n🧪 Test 5: Landing page MCP EU AI Act")

    landing_page_path = "/opt/claude-ceo/workspace/arkwatch/site/mcp-eu-ai-act.html"
    assert os.path.exists(landing_page_path), "La landing page doit exister"

    # Vérifier que le JavaScript checkout est présent
    with open(landing_page_path, "r") as f:
        content = f.read()

    assert "createCheckoutSession" in content, "Le JS de checkout doit être présent"
    assert "/api/checkout/mcp-eu-ai-act" in content, "L'endpoint doit être appelé"
    print("   ✅ Landing page correctement configurée!")


def test_success_page_exists():
    """Test que la page de succès existe"""
    print("\n🧪 Test 6: Page de succès checkout")

    success_page_path = "/opt/claude-ceo/workspace/arkwatch/site/mcp-success.html"
    assert os.path.exists(success_page_path), "La page de succès doit exister"

    # Vérifier le contenu
    with open(success_page_path, "r") as f:
        content = f.read()

    assert "14-day free trial" in content.lower(), "Mention du trial doit être présente"
    assert "MCP EU AI Act" in content, "Mention du produit doit être présente"
    print("   ✅ Page de succès correctement configurée!")


def main():
    """Exécuter tous les tests d'intégration"""
    print("=" * 70)
    print("🚀 Tests d'intégration MCP EU AI Act Checkout")
    print("=" * 70)

    try:
        test_stripe_price_env_var()
        test_mcp_info_endpoint()
        test_checkout_endpoint_validation()
        test_api_routes()
        test_landing_page_exists()
        test_success_page_exists()

        print("\n" + "=" * 70)
        print("✅ Tous les tests d'intégration sont passés!")
        print("=" * 70)
        print("\n📋 Résumé de l'intégration:")
        print(f"   ✓ Produit Stripe créé")
        print(f"   ✓ Price ID: {os.getenv('STRIPE_PRICE_MCP_EU_AI_ACT')}")
        print(f"   ✓ Endpoint /api/checkout/mcp-eu-ai-act opérationnel")
        print(f"   ✓ Landing page intégrée avec boutons checkout")
        print(f"   ✓ Page de succès créée")
        print(f"   ✓ Validation des données fonctionnelle")
        print("\n🎯 Prochaines étapes:")
        print("   1. Tester le flux complet avec un vrai paiement Stripe")
        print("   2. Vérifier les webhooks Stripe")
        print("   3. Tester le trial de 14 jours")
        print("   4. Monitorer les conversions")

        return 0
    except AssertionError as e:
        print(f"\n❌ Test échoué: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
