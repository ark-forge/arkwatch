"""Stripe webhook handler"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ...billing.stripe_service import StripeService
from ..auth import get_user_by_customer_id, update_stripe_info

sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

try:
    from notify_shareholder import send_telegram
    TELEGRAM_ENABLED = True
except ImportError:
    TELEGRAM_ENABLED = False

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

PAYMENTS_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/payments.json")


def record_payment(invoice: dict, email: str | None = None):
    """Record a successful payment to payments.json"""
    try:
        # Load existing payments
        payments = []
        if PAYMENTS_FILE.exists():
            with open(PAYMENTS_FILE) as f:
                payments = json.load(f)

        # Extract payment details
        amount_paid = invoice.get("amount_paid", 0) / 100  # Convert cents to EUR
        currency = invoice.get("currency", "eur").upper()
        invoice_id = invoice.get("id")
        subscription_id = invoice.get("subscription")
        created_timestamp = invoice.get("created")

        # Create payment record
        payment_record = {
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
            "customer_email": email,
            "amount": amount_paid,
            "currency": currency,
            "status": "paid",
            "paid_at": datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else datetime.utcnow().isoformat(),
            "recorded_at": datetime.utcnow().isoformat(),
        }

        # Check if payment already recorded (avoid duplicates)
        if not any(p.get("invoice_id") == invoice_id for p in payments):
            payments.append(payment_record)

            # Write back to file
            with open(PAYMENTS_FILE, "w") as f:
                json.dump(payments, f, indent=2)

            logger.info(f"Payment recorded: {amount_paid} {currency} for {email}")
        else:
            logger.debug(f"Payment {invoice_id} already recorded, skipping")

    except Exception as e:
        logger.error(f"Failed to record payment: {e}", exc_info=True)


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
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature") from e

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
    """Handle new subscription (including trial starts)"""
    customer_id = subscription["customer"]
    subscription_id = subscription["id"]
    status = subscription["status"]

    user = get_user_by_customer_id(customer_id)
    if not user:
        logger.warning(f"No user found for customer {customer_id}")
        return

    key_hash, user_data = user
    tier = StripeService.get_tier_from_subscription(subscription)

    # Grant tier access immediately (active or trialing)
    update_stripe_info(key_hash, subscription_id=subscription_id, subscription_status=status, tier=tier)

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

    # Grant tier access during trial and active periods
    if status in ("active", "trialing"):
        update_stripe_info(key_hash, subscription_id=subscription_id, subscription_status=status, tier=tier)
    else:
        update_stripe_info(key_hash, subscription_id=subscription_id, subscription_status=status)

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
    update_stripe_info(key_hash, subscription_id=None, subscription_status="canceled", tier="free")

    logger.info(f"Subscription deleted for {user_data['email']}, downgraded to free")


async def handle_invoice_paid(invoice: dict):
    """Handle successful payment - records payment, updates revenue, notifies team"""
    customer_id = invoice["customer"]
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return  # Not a subscription invoice

    user = get_user_by_customer_id(customer_id)
    if not user:
        return

    key_hash, user_data = user
    email = user_data.get("email")
    amount = (invoice.get("amount_paid", 0)) / 100  # cents to EUR

    # Ensure subscription is active
    update_stripe_info(key_hash, subscription_status="active")

    # Record payment in payments.json
    record_payment(invoice, email)

    # Update CEO state revenue (Stripe-verified)
    if amount > 0:
        tier = StripeService.get_tier_from_subscription(
            StripeService.get_subscription(subscription_id)
        ) if subscription_id else "unknown"
        update_ceo_state_revenue(amount, email, tier)
        notify_conversion_telegram(email, tier, amount, "active")

    logger.info(f"Invoice paid for {email}: {amount} EUR")


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
    """Handle checkout session completion (including trial signups)"""
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

    # Determine status: if subscription has a trial, status will be "trialing"
    sub_status = "active"
    if subscription_id:
        sub_details = StripeService.get_subscription(subscription_id)
        if sub_details and sub_details.get("status") == "trialing":
            sub_status = "trialing"

    update_stripe_info(key_hash, subscription_id=subscription_id, subscription_status=sub_status, tier=tier or "starter")

    logger.info(f"Checkout completed for {user_data['email']}: {tier} ({sub_status})")

    # Record conversion for tracking
    record_conversion(session, user_data.get("email"), tier or "starter", sub_status)

    # Notify team of new conversion (email + Telegram)
    notify_conversion(user_data.get("email"), tier or "starter", sub_status, session.get("metadata", {}))
    amount = (session.get("amount_total") or 0) / 100
    notify_conversion_telegram(user_data.get("email"), tier or "starter", amount, sub_status)


CONVERSIONS_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/conversions.json")
CEO_STATE_FILE = Path("/opt/claude-ceo/brain/ceo_state.json")
NOTIFY_EMAIL = "apps.desiorac@gmail.com"


def update_ceo_state_revenue(amount: float, email: str | None, tier: str):
    """Update ceo_state.json revenue with Stripe-verified payment.

    Uses the same guard logic as save_ceo_state(stripe_verified=True):
    only updates revenue when called from a verified Stripe webhook.
    """
    try:
        if not CEO_STATE_FILE.exists():
            return

        with open(CEO_STATE_FILE) as f:
            state = json.load(f)

        old_revenue = state.get("revenus", 0)
        new_revenue = old_revenue + amount

        state["revenus"] = new_revenue
        state["last_stripe_payment"] = {
            "amount": amount,
            "email": email,
            "tier": tier,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stripe_verified": True,
        }

        # Atomic write
        tmp = CEO_STATE_FILE.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp), str(CEO_STATE_FILE))

        logger.info(f"CEO state revenue updated: {old_revenue} -> {new_revenue} EUR (Stripe verified)")
    except Exception as e:
        logger.error(f"Failed to update CEO state revenue: {e}", exc_info=True)


def notify_conversion_telegram(email: str | None, tier: str, amount: float, status: str):
    """Send Telegram notification on successful payment/conversion."""
    if not TELEGRAM_ENABLED:
        logger.info(f"Telegram not available, skipping conversion notification")
        return

    status_emoji = "💰" if status == "active" else "🎯"
    status_label = "PAIEMENT REÇU" if status == "active" else "NOUVEL ESSAI"

    message = (
        f"{status_emoji} *{status_label}*\n\n"
        f"Email: `{email or 'N/A'}`\n"
        f"Plan: *{tier.upper()}*\n"
        f"Montant: *{amount:.2f} EUR*\n"
        f"Status: {status}\n"
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"🚀 Premier revenu ArkWatch !"
    )

    try:
        send_telegram(message)
        logger.info(f"Telegram conversion notification sent for {email}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")


def record_conversion(session: dict, email: str | None, tier: str, status: str):
    """Record a checkout conversion event."""
    try:
        conversions = []
        if CONVERSIONS_FILE.exists():
            with open(CONVERSIONS_FILE) as f:
                conversions = json.load(f)

        record = {
            "session_id": session.get("id"),
            "customer_id": session.get("customer"),
            "email": email,
            "tier": tier,
            "status": status,
            "source": session.get("metadata", {}).get("source", "unknown"),
            "product": session.get("metadata", {}).get("product", "arkwatch"),
            "amount_total": (session.get("amount_total") or 0) / 100,
            "currency": session.get("currency", "eur"),
            "converted_at": datetime.utcnow().isoformat(),
        }

        if not any(c.get("session_id") == record["session_id"] for c in conversions):
            conversions.append(record)
            tmp = CONVERSIONS_FILE.with_suffix(".json.tmp")
            with open(tmp, "w") as f:
                json.dump(conversions, f, indent=2)
            tmp.replace(CONVERSIONS_FILE)
            logger.info(f"Conversion recorded: {email} -> {tier} ({status})")

    except Exception as e:
        logger.error(f"Failed to record conversion: {e}", exc_info=True)


def notify_conversion(email: str | None, tier: str, status: str, metadata: dict):
    """Send instant email notification to team about new conversion."""
    if not EMAIL_ENABLED:
        logger.info(f"[DRY RUN] Would notify conversion: {email} -> {tier}")
        return

    source = metadata.get("source", "unknown")
    product = metadata.get("product", "arkwatch")
    status_label = "ESSAI GRATUIT" if status == "trialing" else "ABONNEMENT PAYANT"

    subject = f"[CONVERSION] {status_label}: {email} -> {tier.upper()}"

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
<div style="background: linear-gradient(135deg, #059669, #047857); color: white; padding: 25px; border-radius: 12px; text-align: center;">
    <h1 style="margin: 0; font-size: 24px;">Nouvelle Conversion !</h1>
    <p style="margin: 8px 0 0; opacity: 0.9; font-size: 1.1rem;">{status_label}</p>
</div>
<div style="background: white; padding: 25px; border-radius: 12px; border: 1px solid #e5e7eb; margin-top: 15px;">
    <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 8px 0; font-weight: 700; width: 120px;">Email</td><td>{email or 'N/A'}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Produit</td><td>{product}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Tier</td><td>{tier}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Status</td><td>{status}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Source</td><td>{source}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Date</td><td>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
    </table>
</div>
</body></html>"""

    text_body = f"Nouvelle conversion: {email} -> {tier} ({status}) via {source}"

    try:
        send_email(
            to_addr=NOTIFY_EMAIL,
            subject=subject,
            body=text_body,
            html_body=html_body,
            skip_warmup=True,
        )
    except Exception as e:
        logger.error(f"Failed to send conversion notification: {e}")
