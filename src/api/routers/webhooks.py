"""Stripe webhook handler"""
import logging
from fastapi import APIRouter, Request, HTTPException

from ..auth import update_stripe_info, get_user_by_customer_id
from ...billing.stripe_service import StripeService

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = StripeService.construct_webhook_event(payload, sig_header)
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Received Stripe webhook: {event_type}")

    # Handle subscription events
    if event_type == "customer.subscription.created":
        await handle_subscription_created(data)

    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(data)

    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(data)

    elif event_type == "invoice.paid":
        await handle_invoice_paid(data)

    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(data)

    elif event_type == "checkout.session.completed":
        await handle_checkout_completed(data)

    return {"status": "ok"}


async def handle_subscription_created(subscription: dict):
    """Handle new subscription"""
    customer_id = subscription["customer"]
    subscription_id = subscription["id"]
    status = subscription["status"]

    user = get_user_by_customer_id(customer_id)
    if not user:
        logger.warning(f"No user found for customer {customer_id}")
        return

    key_hash, user_data = user
    tier = StripeService.get_tier_from_subscription(subscription)

    update_stripe_info(
        key_hash,
        subscription_id=subscription_id,
        subscription_status=status,
        tier=tier
    )

    logger.info(f"Subscription created for {user_data['email']}: {tier} ({status})")


async def handle_subscription_updated(subscription: dict):
    """Handle subscription update (upgrade/downgrade/status change)"""
    customer_id = subscription["customer"]
    subscription_id = subscription["id"]
    status = subscription["status"]

    user = get_user_by_customer_id(customer_id)
    if not user:
        logger.warning(f"No user found for customer {customer_id}")
        return

    key_hash, user_data = user
    tier = StripeService.get_tier_from_subscription(subscription)

    # If subscription is active, update tier; otherwise keep current tier
    if status == "active":
        update_stripe_info(
            key_hash,
            subscription_id=subscription_id,
            subscription_status=status,
            tier=tier
        )
    else:
        update_stripe_info(
            key_hash,
            subscription_id=subscription_id,
            subscription_status=status
        )

    logger.info(f"Subscription updated for {user_data['email']}: {tier} ({status})")


async def handle_subscription_deleted(subscription: dict):
    """Handle subscription cancellation"""
    customer_id = subscription["customer"]

    user = get_user_by_customer_id(customer_id)
    if not user:
        logger.warning(f"No user found for customer {customer_id}")
        return

    key_hash, user_data = user

    # Downgrade to free tier
    update_stripe_info(
        key_hash,
        subscription_id=None,
        subscription_status="canceled",
        tier="free"
    )

    logger.info(f"Subscription deleted for {user_data['email']}, downgraded to free")


async def handle_invoice_paid(invoice: dict):
    """Handle successful payment"""
    customer_id = invoice["customer"]
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return  # Not a subscription invoice

    user = get_user_by_customer_id(customer_id)
    if not user:
        return

    key_hash, user_data = user

    # Ensure subscription is active
    update_stripe_info(key_hash, subscription_status="active")

    logger.info(f"Invoice paid for {user_data['email']}")


async def handle_payment_failed(invoice: dict):
    """Handle failed payment"""
    customer_id = invoice["customer"]

    user = get_user_by_customer_id(customer_id)
    if not user:
        return

    key_hash, user_data = user

    update_stripe_info(key_hash, subscription_status="past_due")

    logger.warning(f"Payment failed for {user_data['email']}")


async def handle_checkout_completed(session: dict):
    """Handle checkout session completion"""
    customer_id = session["customer"]
    subscription_id = session.get("subscription")
    tier = session.get("metadata", {}).get("tier")

    if not subscription_id:
        return

    user = get_user_by_customer_id(customer_id)
    if not user:
        logger.warning(f"No user found for customer {customer_id}")
        return

    key_hash, user_data = user

    update_stripe_info(
        key_hash,
        subscription_id=subscription_id,
        subscription_status="active",
        tier=tier or "starter"
    )

    logger.info(f"Checkout completed for {user_data['email']}: {tier}")
