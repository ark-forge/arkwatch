"""Endpoint checkout spécifique pour MCP EU AI Act"""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from ...billing.stripe_service import StripeService

router = APIRouter(prefix="/api/checkout", tags=["MCP Checkout"])

APP_URL = os.getenv("APP_URL", "https://arkforge.fr")


class MCPCheckoutRequest(BaseModel):
    """Requête pour créer une session de checkout MCP EU AI Act"""
    email: EmailStr
    name: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None
    promotion_code: str | None = None
    trial_days: int = 30  # 30 jours (cohérent avec landing page)


class MCPCheckoutResponse(BaseModel):
    """Réponse contenant l'URL de checkout"""
    checkout_url: str
    session_id: str
    product: str = "MCP EU AI Act Compliance Monitoring"
    price: str = "5€/mois"
    trial_days: int = 30


@router.post("/mcp-eu-ai-act", response_model=MCPCheckoutResponse)
async def create_mcp_checkout(request: MCPCheckoutRequest):
    """
    Créer une session Stripe Checkout pour MCP EU AI Act (5€/mois)

    Ce endpoint permet de créer directement une session de paiement sans authentification préalable.
    Parfait pour les landing pages et les conversions rapides.

    - **email**: Email du client (obligatoire)
    - **name**: Nom du client (optionnel)
    - **trial_days**: Nombre de jours de trial (14 par défaut)
    - **promotion_code**: Code promo optionnel
    """
    # Récupérer le Price ID depuis les variables d'environnement
    price_id = os.getenv("STRIPE_PRICE_MCP_EU_AI_ACT")
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail="Configuration Stripe manquante. Contactez le support."
        )

    # URLs de redirection
    success_url = request.success_url or f"{APP_URL}/mcp-success.html?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.cancel_url or f"{APP_URL}/mcp-eu-ai-act.html"

    try:
        # Créer ou récupérer le client Stripe
        # On cherche d'abord si le client existe déjà par email
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

        existing_customers = stripe.Customer.list(email=request.email, limit=1)

        if existing_customers.data:
            customer_id = existing_customers.data[0].id
        else:
            # Créer un nouveau client
            customer = stripe.Customer.create(
                email=request.email,
                name=request.name or request.email.split("@")[0],
                metadata={
                    "product": "mcp-eu-ai-act",
                    "source": "landing_page"
                }
            )
            customer_id = customer.id

        # Créer la session de checkout
        session_params = {
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "product": "mcp-eu-ai-act",
                "tier": "starter"
            },
            "allow_promotion_codes": True,
            "customer_update": {
                "name": "auto",
                "address": "auto"
            }
        }

        # Ajouter le trial gratuit
        if request.trial_days and request.trial_days > 0:
            session_params["subscription_data"] = {
                "trial_period_days": request.trial_days,
                "metadata": {
                    "product": "mcp-eu-ai-act"
                }
            }
            session_params["payment_method_collection"] = "if_required"
        else:
            session_params["payment_method_types"] = ["card"]

        # Appliquer un code promo si fourni
        if request.promotion_code:
            promo_codes = stripe.PromotionCode.list(
                code=request.promotion_code,
                active=True,
                limit=1
            )
            if promo_codes.data:
                session_params.pop("allow_promotion_codes", None)
                session_params["discounts"] = [{"promotion_code": promo_codes.data[0].id}]

        session = stripe.checkout.Session.create(**session_params)

        return MCPCheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
            trial_days=request.trial_days
        )

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur Stripe: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du checkout: {str(e)}"
        ) from e


@router.get("/mcp-eu-ai-act/info")
async def get_mcp_info():
    """
    Récupérer les informations sur le produit MCP EU AI Act

    Endpoint public pour afficher les détails du produit sans authentification.
    """
    return {
        "product": "MCP EU AI Act Compliance Monitoring",
        "description": "Monitor EU AI Act compliance changes in real-time with automated alerts",
        "price": {
            "amount": 5,
            "currency": "EUR",
            "interval": "month",
            "trial_days": 30
        },
        "features": [
            "Model Card Protocol tracking",
            "Real-time compliance alerts",
            "Compliance dashboard",
            "Risk assessment monitoring",
            "Audit-ready reports",
            "Email notifications"
        ],
        "checkout_endpoint": "/api/checkout/mcp-eu-ai-act"
    }
