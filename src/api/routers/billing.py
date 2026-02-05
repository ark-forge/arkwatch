"""Billing endpoints for Stripe subscriptions"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from ..auth import (
    get_current_user,
    update_stripe_info,
    get_user_by_customer_id,
    get_key_hash_for_user,
)
from ...billing.stripe_service import StripeService

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

APP_URL = os.getenv("APP_URL", "https://arkforge.fr")


class CheckoutRequest(BaseModel):
    tier: str  # starter, pro, business
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class SubscriptionResponse(BaseModel):
    tier: str
    status: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool = False
    stripe_customer_id: Optional[str]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(user: dict = Depends(get_current_user)):
    """Get current subscription status"""
    subscription_id = user.get("stripe_subscription_id")

    if not subscription_id:
        return SubscriptionResponse(
            tier=user.get("tier", "free"),
            status=user.get("subscription_status"),
            current_period_end=None,
            cancel_at_period_end=False,
            stripe_customer_id=user.get("stripe_customer_id"),
        )

    sub_details = StripeService.get_subscription(subscription_id)

    if sub_details:
        return SubscriptionResponse(
            tier=sub_details["tier"],
            status=sub_details["status"],
            current_period_end=sub_details["current_period_end"],
            cancel_at_period_end=sub_details["cancel_at_period_end"],
            stripe_customer_id=user.get("stripe_customer_id"),
        )
    else:
        return SubscriptionResponse(
            tier=user.get("tier", "free"),
            status="unknown",
            current_period_end=None,
            cancel_at_period_end=False,
            stripe_customer_id=user.get("stripe_customer_id"),
        )


@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    user: dict = Depends(get_current_user)
):
    """Create a Stripe Checkout session for upgrading subscription"""
    if request.tier not in ["starter", "pro", "business"]:
        raise HTTPException(status_code=400, detail="Invalid tier. Must be: starter, pro, or business")

    key_hash = get_key_hash_for_user(user)
    if not key_hash:
        raise HTTPException(status_code=500, detail="User not found")

    # Get or create Stripe customer
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer_id = StripeService.create_customer(
            email=user["email"],
            name=user["name"],
            api_key_hash=key_hash
        )
        update_stripe_info(key_hash, customer_id=customer_id)

    # Create checkout session
    success_url = request.success_url or f"{APP_URL}/arkwatch/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.cancel_url or f"{APP_URL}/arkwatch/billing/cancel"

    try:
        session = StripeService.create_checkout_session(
            customer_id=customer_id,
            tier=request.tier,
            success_url=success_url,
            cancel_url=cancel_url
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/portal")
async def create_portal_session(user: dict = Depends(get_current_user)):
    """Create a Stripe Billing Portal session for managing subscription"""
    customer_id = user.get("stripe_customer_id")

    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found. Please subscribe first."
        )

    return_url = f"{APP_URL}/arkwatch/dashboard"

    try:
        session = StripeService.create_billing_portal_session(
            customer_id=customer_id,
            return_url=return_url
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel the current subscription (at period end)"""
    subscription_id = user.get("stripe_subscription_id")

    if not subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    try:
        result = StripeService.cancel_subscription(subscription_id, at_period_end=True)

        # Update user record
        key_hash = get_key_hash_for_user(user)
        if key_hash:
            update_stripe_info(key_hash, subscription_status="canceling")

        return {
            "message": "Subscription will be cancelled at the end of the billing period",
            "cancel_at_period_end": result["cancel_at_period_end"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.get("/usage")
async def get_usage(user: dict = Depends(get_current_user)):
    """Get current usage vs limits"""
    from ...storage.database import Database
    from ..auth import get_tier_limits

    db = Database()
    watches = db.get_watches_by_user(user.get("email", ""))

    limits = get_tier_limits(user.get("tier", "free"))

    return {
        "tier": user.get("tier", "free"),
        "watches_used": len(watches),
        "watches_limit": limits["max_watches"],
        "check_interval_min": limits["check_interval_min"],
        "subscription_status": user.get("subscription_status"),
    }
