#!/usr/bin/env python3
"""Script pour créer le produit Stripe MCP EU AI Act"""

import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import stripe

# Charger les clés depuis .env.stripe
def load_stripe_key():
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env.stripe")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("STRIPE_SECRET_KEY="):
                    return line.split("=", 1)[1]
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY non trouvée dans .env.stripe ni dans l'environnement")
    return key

stripe.api_key = load_stripe_key()


def create_mcp_product():
    """Créer le produit MCP EU AI Act dans Stripe"""
    print("🔍 Recherche du produit existant MCP EU AI Act...")

    # Vérifier si le produit existe déjà
    existing_products = stripe.Product.list(limit=100)
    for product in existing_products.data:
        if "MCP EU AI Act" in product.name or "mcp-eu-ai-act" in product.get("metadata", {}).get("slug", ""):
            print(f"✅ Produit existant trouvé: {product.name} (ID: {product.id})")
            return product

    print("➕ Création du nouveau produit MCP EU AI Act...")

    # Créer le produit
    product = stripe.Product.create(
        name="MCP EU AI Act Compliance Monitoring",
        description="Monitor EU AI Act compliance changes in real-time. Model Card Protocol tracking with automated alerts.",
        metadata={
            "slug": "mcp-eu-ai-act",
            "category": "compliance",
            "features": "model-card-tracking,real-time-alerts,compliance-dashboard,risk-assessment,audit-reports"
        },
        active=True
    )

    print(f"✅ Produit créé: {product.name} (ID: {product.id})")
    return product


def create_price(product_id):
    """Créer le prix 9€/mois pour le produit"""
    print(f"\n💰 Création du prix 9€/mois pour le produit {product_id}...")

    # Vérifier si le prix existe déjà
    existing_prices = stripe.Price.list(product=product_id, limit=10)
    for price in existing_prices.data:
        if price.unit_amount == 900 and price.currency == "eur" and price.recurring and price.recurring.interval == "month":
            print(f"✅ Prix existant trouvé: 9€/mois (ID: {price.id})")
            return price

    # Créer le prix
    price = stripe.Price.create(
        product=product_id,
        unit_amount=900,  # 9€ en centimes
        currency="eur",
        recurring={
            "interval": "month",
            "interval_count": 1,
            "trial_period_days": 14
        },
        metadata={
            "tier": "mcp-starter",
            "display_name": "MCP Starter"
        }
    )

    print(f"✅ Prix créé: 9€/mois (ID: {price.id})")
    return price


def update_env_file(price_id):
    """Ajouter le price ID au fichier .env.stripe"""
    env_file = "/opt/claude-ceo/workspace/arkwatch/.env.stripe"

    print(f"\n📝 Mise à jour du fichier {env_file}...")

    with open(env_file, "r") as f:
        content = f.read()

    # Ajouter la nouvelle variable si elle n'existe pas
    if "STRIPE_PRICE_MCP_EU_AI_ACT" not in content:
        new_line = f"\n# MCP EU AI Act Product\nSTRIPE_PRICE_MCP_EU_AI_ACT={price_id}\n"
        content += new_line

        with open(env_file, "w") as f:
            f.write(content)

        print(f"✅ Variable STRIPE_PRICE_MCP_EU_AI_ACT ajoutée avec la valeur: {price_id}")
    else:
        print("ℹ️  Variable STRIPE_PRICE_MCP_EU_AI_ACT déjà présente")


def main():
    print("🚀 Configuration du produit Stripe MCP EU AI Act\n")
    print("=" * 60)

    # Créer le produit
    product = create_mcp_product()

    # Créer le prix
    price = create_price(product.id)

    # Mettre à jour .env.stripe
    update_env_file(price.id)

    print("\n" + "=" * 60)
    print("✅ Configuration terminée!\n")
    print("📋 Résumé:")
    print(f"   - Produit ID: {product.id}")
    print(f"   - Produit nom: {product.name}")
    print(f"   - Prix ID: {price.id}")
    print(f"   - Prix: 9€/mois")
    print(f"   - Trial: 14 jours")
    print(f"\n🔗 URL de paiement direct:")
    print(f"   https://buy.stripe.com/create?price={price.id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)
