"""ArkWatch direct checkout endpoint for conversion emails.

Creates Stripe checkout sessions for ArkWatch plans (Starter/Pro/Business)
without requiring prior authentication. Designed for email CTAs and landing pages.

Payment links fallback:
- Starter: https://buy.stripe.com/00w7sE8li8aU2iA8Uo4AU04
- Pro: https://buy.stripe.com/5kQ28k6dagHq9L2eeI4AU05
- Business: https://buy.stripe.com/9B6dR2bxucra0aseeI4AU06
"""

import logging
import os

import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/checkout", tags=["ArkWatch Checkout"])
logger = logging.getLogger(__name__)

APP_URL = os.getenv("APP_URL", "https://arkforge.fr")

TIER_CONFIG = {
    "starter": {
        "price_env": "STRIPE_PRICE_STARTER",
        "label": "ArkWatch Starter",
        "price_display": "9EUR/mois",
        "trial_days": 14,
    },
    "pro": {
        "price_env": "STRIPE_PRICE_PRO",
        "label": "ArkWatch Pro",
        "price_display": "29EUR/mois",
        "trial_days": 14,
    },
    "business": {
        "price_env": "STRIPE_PRICE_BUSINESS",
        "label": "ArkWatch Business",
        "price_display": "99EUR/mois",
        "trial_days": 14,
    },
}


class ArkWatchCheckoutRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    tier: str = "starter"
    trial_days: int | None = 14
    promotion_code: str | None = None
    source: str = "email_cta"
    success_url: str | None = None
    cancel_url: str | None = None


class ArkWatchCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    product: str
    price: str
    trial_days: int


@router.post("/arkwatch", response_model=ArkWatchCheckoutResponse)
async def create_arkwatch_checkout(request: ArkWatchCheckoutRequest):
    """Create a Stripe Checkout session for any ArkWatch tier.

    Used by email CTAs and landing pages for direct conversion.
    No authentication required.
    """
    tier_info = TIER_CONFIG.get(request.tier)
    if not tier_info:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")

    price_id = os.getenv(tier_info["price_env"])
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price not configured")

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    success_url = request.success_url or f"{APP_URL}/trial-14d.html?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.cancel_url or f"{APP_URL}/pricing.html"

    trial_days = request.trial_days if request.trial_days is not None else tier_info["trial_days"]

    try:
        # Find or create Stripe customer
        existing = stripe.Customer.list(email=request.email, limit=1)
        if existing.data:
            customer_id = existing.data[0].id
        else:
            customer = stripe.Customer.create(
                email=request.email,
                name=request.name or request.email.split("@")[0],
                metadata={
                    "product": "arkwatch",
                    "tier": request.tier,
                    "source": request.source,
                },
            )
            customer_id = customer.id

        session_params = {
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "product": "arkwatch",
                "tier": request.tier,
                "source": request.source,
            },
            "allow_promotion_codes": True,
            "customer_update": {"name": "auto", "address": "auto"},
        }

        if trial_days and trial_days > 0:
            session_params["subscription_data"] = {
                "trial_period_days": trial_days,
                "metadata": {"product": "arkwatch", "tier": request.tier},
            }
            session_params["payment_method_collection"] = "if_required"
        else:
            session_params["payment_method_types"] = ["card"]

        if request.promotion_code:
            promo_codes = stripe.PromotionCode.list(
                code=request.promotion_code, active=True, limit=1
            )
            if promo_codes.data:
                session_params.pop("allow_promotion_codes", None)
                session_params["discounts"] = [{"promotion_code": promo_codes.data[0].id}]

        session = stripe.checkout.Session.create(**session_params)

        logger.info(f"Checkout created for {request.email}: {request.tier} (source={request.source})")

        return ArkWatchCheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
            product=tier_info["label"],
            price=tier_info["price_display"],
            trial_days=trial_days or 0,
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error for {request.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur paiement: {str(e)}") from e


@router.get("/arkwatch/tiers")
async def get_arkwatch_tiers():
    """Public endpoint returning available ArkWatch tiers and pricing."""
    return {
        "tiers": [
            {
                "id": tid,
                "name": cfg["label"],
                "price": cfg["price_display"],
                "trial_days": cfg["trial_days"],
                "checkout_endpoint": "/api/checkout/arkwatch",
            }
            for tid, cfg in TIER_CONFIG.items()
        ]
    }
