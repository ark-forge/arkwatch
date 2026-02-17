#!/usr/bin/env python3
"""
Stripe Invoice Generator - ArkWatch
Génère et envoie des factures Stripe pour conversion manuelle leads→clients
Usage: python3 stripe_invoice_script.py --email prospect@company.com --tier pro --send-email
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import stripe
except ImportError:
    print("ERROR: stripe package not installed")
    print("Run: pip install stripe")
    sys.exit(1)


# Configuration Stripe (Load from .env.stripe)
STRIPE_ENV_FILE = Path("/opt/arkwatch/api/.env.stripe")
STRIPE_SECRET_KEY = None
STRIPE_PRODUCT_ID = "prod_TvmgE1PETPHF6G"  # ArkWatch product

# Price IDs par tier
TIER_PRICES = {
    "starter": {
        "price_id": "price_1Sxv716iihEhp9U9W5BSeNbK",
        "amount": 9.00,
        "currency": "EUR",
        "interval": "monthly"
    },
    "pro": {
        "price_id": "price_1Sxv716iihEhp9U9VBl5cnxR",
        "amount": 29.00,
        "currency": "EUR",
        "interval": "monthly"
    },
    "business": {
        "price_id": "price_1Sxv716iihEhp9U9ilPBpzAV",
        "amount": 99.00,
        "currency": "EUR",
        "interval": "monthly"
    }
}

# Log file pour tracking
INVOICE_LOG_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/invoices_generated.json")


def load_stripe_config():
    """Load Stripe API key from .env.stripe file."""
    global STRIPE_SECRET_KEY

    if not STRIPE_ENV_FILE.exists():
        print(f"ERROR: Stripe config file not found: {STRIPE_ENV_FILE}")
        print("Expected file: /opt/arkwatch/api/.env.stripe")
        sys.exit(1)

    with open(STRIPE_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("STRIPE_SECRET_KEY="):
                STRIPE_SECRET_KEY = line.split("=", 1)[1]
                break

    if not STRIPE_SECRET_KEY:
        print("ERROR: STRIPE_SECRET_KEY not found in .env.stripe")
        sys.exit(1)

    stripe.api_key = STRIPE_SECRET_KEY
    print(f"✅ Stripe API key loaded (ends with: ...{STRIPE_SECRET_KEY[-8:]})")


def validate_tier(tier: str) -> dict:
    """Validate tier and return price config."""
    tier_lower = tier.lower()
    if tier_lower not in TIER_PRICES:
        print(f"ERROR: Invalid tier '{tier}'")
        print(f"Valid tiers: {', '.join(TIER_PRICES.keys())}")
        sys.exit(1)
    return TIER_PRICES[tier_lower]


def get_or_create_customer(email: str, name: str = None) -> str:
    """Get existing Stripe customer or create new one."""
    print(f"\n[1/4] Checking for existing Stripe customer: {email}")

    # Search for existing customer
    customers = stripe.Customer.list(email=email, limit=1)

    if customers.data:
        customer = customers.data[0]
        print(f"  → Found existing customer: {customer.id}")
        return customer.id

    # Create new customer
    print(f"  → Creating new customer...")
    if not name:
        name = email.split("@")[0].capitalize()

    customer = stripe.Customer.create(
        email=email,
        name=name,
        description=f"ArkWatch trial conversion - {datetime.now(timezone.utc).isoformat()}"
    )

    print(f"  → Created customer: {customer.id}")
    return customer.id


def create_invoice(customer_id: str, price_config: dict, tier: str, description: str = None) -> dict:
    """Create Stripe Invoice for subscription (draft mode)."""
    print(f"\n[2/4] Creating invoice for tier: {tier.upper()}")

    if not description:
        description = f"ArkWatch {tier.capitalize()} - Abonnement mensuel"

    # Create invoice item
    invoice_item = stripe.InvoiceItem.create(
        customer=customer_id,
        price=price_config["price_id"],
        description=description
    )

    print(f"  → Invoice item created: {invoice_item.id}")

    # Create invoice (draft)
    invoice = stripe.Invoice.create(
        customer=customer_id,
        auto_advance=True,  # Auto-finalize when sent
        collection_method="send_invoice",
        days_until_due=7,  # 7 days to pay
        description=description,
        metadata={
            "product": "arkwatch",
            "tier": tier,
            "conversion_type": "manual_trial",
            "created_via": "stripe_invoice_script"
        }
    )

    print(f"  → Invoice created (draft): {invoice.id}")
    print(f"  → Amount: {price_config['amount']} {price_config['currency'].upper()}")
    print(f"  → Due date: 7 days after sending")

    return invoice


def send_invoice(invoice_id: str, email: str) -> bool:
    """Finalize and send invoice to customer."""
    print(f"\n[3/4] Sending invoice to: {email}")

    try:
        # Finalize invoice
        invoice = stripe.Invoice.finalize_invoice(invoice_id)
        print(f"  → Invoice finalized: {invoice.status}")

        # Send invoice email
        sent_invoice = stripe.Invoice.send_invoice(invoice_id)
        print(f"  → Invoice email sent: {sent_invoice.status}")
        print(f"  → Customer will receive email from Stripe")
        print(f"  → Hosted invoice URL: {sent_invoice.hosted_invoice_url}")

        return True

    except stripe.error.StripeError as e:
        print(f"  ❌ Error sending invoice: {e}")
        return False


def log_invoice(invoice_data: dict):
    """Log invoice creation to tracking file."""
    print(f"\n[4/4] Logging invoice to: {INVOICE_LOG_FILE}")

    INVOICE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing logs
    logs = []
    if INVOICE_LOG_FILE.exists():
        try:
            with open(INVOICE_LOG_FILE) as f:
                logs = json.load(f)
        except (json.JSONDecodeError, OSError):
            logs = []

    # Append new log
    logs.append(invoice_data)

    # Save atomically
    tmp_file = str(INVOICE_LOG_FILE) + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, str(INVOICE_LOG_FILE))

    print(f"  → Invoice logged (total: {len(logs)} invoices)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate and send Stripe Invoice for ArkWatch trial conversion"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Customer email address"
    )
    parser.add_argument(
        "--tier",
        required=True,
        choices=["starter", "pro", "business"],
        help="Subscription tier (starter/pro/business)"
    )
    parser.add_argument(
        "--name",
        help="Customer name (optional, extracted from email if not provided)"
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send invoice email to customer (default: draft only)"
    )
    parser.add_argument(
        "--description",
        help="Custom invoice description (optional)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (print only, don't create invoice)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("STRIPE INVOICE GENERATOR - ArkWatch")
    print("=" * 80)

    # Load Stripe config
    load_stripe_config()

    # Validate tier
    price_config = validate_tier(args.tier)

    print("\n📋 Invoice Details:")
    print(f"  Customer: {args.email}")
    print(f"  Tier: {args.tier.upper()}")
    print(f"  Amount: {price_config['amount']} {price_config['currency'].upper()}/{price_config['interval']}")
    print(f"  Send email: {'YES' if args.send_email else 'NO (draft only)'}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No invoice will be created")
        return 0

    # Confirm before proceeding
    print("\n⚠️  This will create a REAL Stripe invoice.")
    confirm = input("Proceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return 1

    try:
        # Get or create customer
        customer_id = get_or_create_customer(args.email, args.name)

        # Create invoice
        invoice = create_invoice(
            customer_id,
            price_config,
            args.tier,
            args.description
        )

        # Send invoice if requested
        sent = False
        if args.send_email:
            sent = send_invoice(invoice.id, args.email)
        else:
            print(f"\n⚠️  Invoice created as DRAFT (not sent)")
            print(f"  → To send later, run:")
            print(f"  stripe.Invoice.send_invoice('{invoice.id}')")

        # Log invoice
        invoice_data = {
            "invoice_id": invoice.id,
            "customer_id": customer_id,
            "customer_email": args.email,
            "tier": args.tier,
            "amount": price_config["amount"],
            "currency": price_config["currency"],
            "status": invoice.status,
            "sent": sent,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            "hosted_invoice_url": invoice.hosted_invoice_url,
            "invoice_pdf": invoice.invoice_pdf if hasattr(invoice, "invoice_pdf") else None
        }
        log_invoice(invoice_data)

        # Summary
        print("\n" + "=" * 80)
        print("✅ INVOICE CREATION COMPLETE")
        print("=" * 80)
        print(f"Invoice ID: {invoice.id}")
        print(f"Customer: {args.email}")
        print(f"Amount: {price_config['amount']} {price_config['currency'].upper()}")
        print(f"Status: {invoice.status}")
        print(f"Sent: {'YES' if sent else 'NO (draft)'}")
        print(f"URL: {invoice.hosted_invoice_url}")

        if sent:
            print("\n📧 Customer will receive an email from Stripe with:")
            print("  - Invoice details")
            print("  - Payment link (secure Stripe page)")
            print("  - Due date: 7 days")

        print("\n📊 Next steps:")
        print("  1. Wait for customer payment")
        print("  2. Stripe webhook will activate subscription automatically")
        print("  3. Check payment in: /opt/claude-ceo/workspace/arkwatch/data/payments.json")
        print("=" * 80)

        return 0

    except stripe.error.StripeError as e:
        print(f"\n❌ Stripe API Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
