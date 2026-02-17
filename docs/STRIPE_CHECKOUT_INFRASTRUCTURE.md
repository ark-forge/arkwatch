# Infrastructure Stripe Checkout + Webhooks - ArkWatch
**Date**: 2026-02-09
**Task**: #20260892
**Worker**: Fondations

## ✅ Résumé Exécutif

Infrastructure complète de paiement Stripe **DÉJÀ EN PLACE ET FONCTIONNELLE**.

## 📦 Composants Existants

### 1. Configuration Stripe (LIVE MODE)
**Fichier**: `.env.stripe`
```bash
STRIPE_SECRET_KEY=sk_live_REDACTED
STRIPE_PUBLISHABLE_KEY=pk_live_REDACTED
STRIPE_WEBHOOK_SECRET=whsec_REDACTED
STRIPE_CURRENCY=eur
```

### 2. Product & Prices (LIVE)
**Product ID**: `prod_TvmgE1PETPHF6G`

| Tier | Price ID | Montant | Interval |
|------|----------|---------|----------|
| Starter | `price_1Sxv716iihEhp9U9W5BSeNbK` | 9 EUR | monthly |
| Pro | `price_1Sxv716iihEhp9U9VBl5cnxR` | 29 EUR | monthly |
| Business | `price_1Sxv716iihEhp9U9ilPBpzAV` | 99 EUR | monthly |

### 3. Payment Links (Direct Checkout)
**No code required** - liens directs Stripe Checkout :

- **Starter (9€)**: https://buy.stripe.com/00w7sE8li8aU2iA8Uo4AU04
- **Pro (29€)**: https://buy.stripe.com/5kQ28k6dagHq9L2eeI4AU05
- **Business (99€)**: https://buy.stripe.com/9B6dR2bxucra0aseeI4AU06

### 4. API Endpoints (Billing)
**Fichier**: `src/api/routers/billing.py`

#### POST `/api/v1/billing/checkout`
Crée une session Stripe Checkout pour abonnement
```json
Request:
{
  "tier": "starter|pro|business",
  "success_url": "https://arkforge.fr/success.html",
  "cancel_url": "https://arkforge.fr/cancel.html",
  "promotion_code": "EARLY2024",  // optional
  "trial_days": 14  // default 14-day free trial
}

Response:
{
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/..."
}
```

#### GET `/api/v1/billing/subscription`
Obtenir le statut de l'abonnement actuel
```json
Response:
{
  "tier": "pro",
  "status": "active",
  "current_period_end": "2026-03-09T00:00:00",
  "cancel_at_period_end": false,
  "stripe_customer_id": "cus_..."
}
```

#### POST `/api/v1/billing/portal`
Créer une session Stripe Billing Portal (manage/cancel subscription)
```json
Response:
{
  "portal_url": "https://billing.stripe.com/..."
}
```

#### POST `/api/v1/billing/cancel`
Annuler l'abonnement (à la fin de la période)
```json
Response:
{
  "message": "Subscription will be cancelled at the end of the billing period",
  "cancel_at_period_end": true
}
```

#### GET `/api/v1/billing/usage`
Usage actuel vs limites du tier
```json
Response:
{
  "tier": "pro",
  "watches_used": 7,
  "watches_limit": 100,
  "check_interval_min": 5,
  "subscription_status": "active"
}
```

### 5. Webhooks Handler
**Fichier**: `src/api/routers/webhooks.py`
**Endpoint**: `POST /api/v1/webhooks/stripe`

#### Events Gérés
| Event | Action |
|-------|--------|
| `customer.subscription.created` | Grant tier access (active/trialing) |
| `customer.subscription.updated` | Update tier/status |
| `customer.subscription.deleted` | Downgrade to free |
| `invoice.paid` | Confirm payment, record to payments.json |
| `invoice.payment_failed` | Mark as past_due |
| `checkout.session.completed` | Activate trial subscription |

#### Enregistrement Paiements
**Fichier**: `/opt/claude-ceo/workspace/arkwatch/data/payments.json`
```json
[
  {
    "invoice_id": "in_...",
    "subscription_id": "sub_...",
    "customer_email": "user@example.com",
    "amount": 29.0,
    "currency": "EUR",
    "status": "paid",
    "paid_at": "2026-02-09T10:30:00",
    "recorded_at": "2026-02-09T10:30:05"
  }
]
```

### 6. Stripe Service
**Fichier**: `src/billing/stripe_service.py`

Méthodes disponibles :
- `create_customer(email, name, api_key_hash)` → customer_id
- `get_customer(customer_id)` → customer details
- `create_checkout_session(customer_id, tier, success_url, cancel_url, promotion_code, trial_days)` → session
- `create_billing_portal_session(customer_id, return_url)` → portal session
- `get_subscription(subscription_id)` → subscription details
- `cancel_subscription(subscription_id, at_period_end)` → cancellation
- `get_customer_subscriptions(customer_id)` → list of subscriptions
- `construct_webhook_event(payload, sig_header)` → verified event
- `get_tier_from_subscription(subscription)` → tier name

## 🎯 Flux Utilisateur Complet

### 1. Inscription Free Trial (14 jours)
```
User visite: https://arkforge.fr/trial-14d.html?plan=pro
  ↓
Formulaire capture: email + plan
  ↓
POST /api/trial-14d/signup {email, plan, source}
  ↓
Backend crée:
  - User account
  - Stripe customer
  - Checkout session (14-day trial, no CC)
  ↓
Redirect: Stripe Checkout URL
  ↓
User complète signup (no payment method required)
  ↓
Webhook: checkout.session.completed
  ↓
Grant tier access (status: trialing)
  ↓
Email: Welcome + credentials (API key)
```

### 2. Fin du Trial → Conversion Payante
```
J+14: Trial expires
  ↓
Webhook: customer.subscription.updated (status: past_due)
  ↓
Email: "Your trial has ended. Add payment method to continue."
  ↓
User clicks: "Manage Subscription"
  ↓
POST /api/v1/billing/portal
  ↓
Redirect: Stripe Billing Portal
  ↓
User adds payment method
  ↓
First invoice paid
  ↓
Webhook: invoice.paid
  ↓
Grant tier access (status: active)
  ↓
Record payment in payments.json
  ↓
🎉 PREMIER REVENU
```

### 3. Upgrade/Downgrade
```
User dashboard: "Upgrade Plan"
  ↓
POST /api/v1/billing/portal
  ↓
Stripe Billing Portal: Change plan
  ↓
Webhook: customer.subscription.updated
  ↓
Update tier + limits
```

## 🔧 Configuration Webhook Stripe

### Endpoint à configurer dans Stripe Dashboard
```
URL: https://watch.arkforge.fr/api/v1/webhooks/stripe
Secret: whsec_REDACTED (déjà configuré)
```

### Events à écouter
- ✅ `customer.subscription.created`
- ✅ `customer.subscription.updated`
- ✅ `customer.subscription.deleted`
- ✅ `invoice.paid`
- ✅ `invoice.payment_failed`
- ✅ `checkout.session.completed`

## 📊 Dashboard Minimal Subscriptions

**Fichier existant**: Données dans SQLite + payments.json

Pour créer un tableau de bord :
```bash
# Liste des subscriptions actives
SELECT email, tier, subscription_status, stripe_customer_id, stripe_subscription_id
FROM users
WHERE subscription_status IN ('active', 'trialing')
ORDER BY created_at DESC;

# Revenus ce mois (depuis payments.json)
jq '[.[] | select(.paid_at | startswith("2026-02")) | .amount] | add' data/payments.json
```

## ⚠️ Incohérence Tarifaire Détectée

**Tâche demande**: "abonnement mensuel 49€"
**Tarifs configurés**: 9€ / 29€ / 99€

### Solutions proposées :

#### Option A : Utiliser Pro (29€) existant
✅ **Prêt immédiatement**
✅ Cohérent avec pricing actuel
✅ Peut générer revenus sous 5min

#### Option B : Créer nouveau price "Trial" à 49€
⚠️ Nécessite création Stripe price
⚠️ Nécessite mise à jour code + config
⏱️ Délai : ~30 min

### Commande pour créer price 49€ (si nécessaire)
```python
import stripe
stripe.api_key = "sk_live_..."

price = stripe.Price.create(
    product="prod_TvmgE1PETPHF6G",
    unit_amount=4900,  # 49.00 EUR
    currency="eur",
    recurring={"interval": "month"},
    nickname="Trial - 49 EUR/month"
)
print(f"Price ID: {price.id}")
```

## ✅ Ce qui est DÉJÀ prêt

1. ✅ **Stripe Checkout** : 3 tiers fonctionnels (9€/29€/99€)
2. ✅ **Webhooks** : Activation automatique des licenses
3. ✅ **Page de confirmation** : success_url avec credentials
4. ✅ **Enregistrement paiements** : payments.json
5. ✅ **Billing Portal** : Manage/cancel subscription
6. ✅ **Trial 14j** : No credit card required

## 🚀 Action Immédiate

**Un prospect peut payer et recevoir ses accès en <5min** :

1. Visiter : https://buy.stripe.com/5kQ28k6dagHq9L2eeI4AU05 (Pro 29€)
2. Compléter paiement Stripe
3. Webhook active la license
4. Email automatique avec API key
5. ✅ Accès immédiat

## 📝 Documentation Actionnaire

Pour tester le funnel complet :
1. https://arkforge.fr/demo.html → Découverte produit
2. https://arkforge.fr/pricing.html → Choix plan
3. https://arkforge.fr/trial-14d.html?plan=pro → Inscription trial
4. Stripe Checkout → Paiement (ou trial 14j)
5. https://watch.arkforge.fr/api/v1/webhooks/stripe → Activation auto
6. Email → Credentials + onboarding

**Tout est fonctionnel. Décision CEO nécessaire sur le tarif (29€ ou 49€).**
