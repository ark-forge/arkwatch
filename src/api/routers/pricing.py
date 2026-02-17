"""Pricing endpoints for ArkWatch subscription tiers"""

import json
import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])

# Pricing configuration
PRICING_DATA = {
    "product": "arkwatch",
    "currency": "EUR",
    "billing_period": "monthly",
    "tiers": [
        {
            "id": "starter",
            "name": "Starter",
            "price": 9,
            "price_display": "9€",
            "billing_display": "par mois",
            "description": "Pour démarrer avec ArkWatch",
            "features": [
                "3 URLs à surveiller",
                "Vérifications quotidiennes",
                "Alertes email",
                "Historique 30 jours"
            ],
            "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", "price_1Sxv716iihEhp9U9W5BSeNbK"),
            "payment_link": os.getenv("STRIPE_PAYMENT_LINK_STARTER", "https://buy.stripe.com/00w7sE8li8aU2iA8Uo4AU04")
        },
        {
            "id": "pro",
            "name": "Pro",
            "price": 29,
            "price_display": "29€",
            "billing_display": "par mois",
            "description": "Pour les professionnels",
            "features": [
                "25 URLs à surveiller",
                "Vérifications toutes les 6h",
                "Alertes email + Webhook",
                "Historique 90 jours",
                "Comparaison IA des changements"
            ],
            "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_1Sxv716iihEhp9U9VBl5cnxR"),
            "payment_link": os.getenv("STRIPE_PAYMENT_LINK_PRO", "https://buy.stripe.com/5kQ28k6dagHq9L2eeI4AU05")
        },
        {
            "id": "business",
            "name": "Business",
            "price": 99,
            "price_display": "99€",
            "billing_display": "par mois",
            "description": "Pour les entreprises",
            "features": [
                "URLs illimitées",
                "Vérifications toutes les heures",
                "Alertes email + Webhook + API",
                "Historique illimité",
                "Résumés IA avancés",
                "Support prioritaire",
                "SLA 99.9%"
            ],
            "stripe_price_id": os.getenv("STRIPE_PRICE_BUSINESS", "price_1Sxv716iihEhp9U9ilPBpzAV"),
            "payment_link": os.getenv("STRIPE_PAYMENT_LINK_BUSINESS", "https://buy.stripe.com/9B6dR2bxucra0aseeI4AU06")
        }
    ],
    "free_tier": {
        "id": "free",
        "name": "Gratuit",
        "price": 0,
        "price_display": "Gratuit",
        "features": [
            "1 URL à surveiller",
            "Vérifications quotidiennes",
            "Alertes email basiques"
        ]
    },
    "metadata": {
        "version": "1.0.0",
        "last_updated": "2026-02-06"
    }
}


@router.get("/", response_model=dict)
async def get_pricing():
    """Get all pricing tiers and details"""
    return PRICING_DATA


@router.get("/tiers", response_model=list)
async def get_tiers():
    """Get list of available tiers"""
    return PRICING_DATA["tiers"]


@router.get("/{tier_id}", response_model=dict)
async def get_tier_details(tier_id: str):
    """Get details for a specific tier"""
    if tier_id == "free":
        return PRICING_DATA["free_tier"]

    for tier in PRICING_DATA["tiers"]:
        if tier["id"] == tier_id:
            return tier

    return {"error": f"Tier '{tier_id}' not found"}
