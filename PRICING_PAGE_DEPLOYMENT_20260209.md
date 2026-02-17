# Landing Page Pricing ArkWatch - Déploiement Complet
**Date**: 2026-02-09  
**Task**: #20260887  
**Worker**: Fondations

## ✅ Résumé Exécutif

Landing page pricing avec 3 plans (Starter €29, Pro €99, Enterprise custom) et CTA trial 14j **DÉPLOYÉE EN PRODUCTION**.

## 📍 URLs Déployées

- **Pricing**: https://arkforge.fr/pricing.html
- **Demo**: https://arkforge.fr/demo.html  
- **Trial 14j**: https://arkforge.fr/trial-14d.html

## 📋 3 Plans Configurés

### 1. Starter - €29/mois
- Up to 10 monitors
- Check every 15 minutes
- Email alerts + AI summaries
- 10,000 API calls/month
- CTA: "Start 14-Day Free Trial" → `/trial-14d.html?plan=starter`

### 2. Pro - €99/mois (FEATURED)
- Unlimited monitors
- Check every 5 minutes
- Email + SMS alerts
- Unlimited API calls
- Priority support (24h)
- Slack/Teams notifications
- CTA: "Start 14-Day Free Trial" → `/trial-14d.html?plan=pro`

### 3. Enterprise - Custom
- Everything in Pro
- Dedicated infrastructure
- Custom SLA
- On-premise deployment
- SSO integration
- 24/7 priority support
- CTA: "Contact Sales" → `mailto:contact@arkforge.fr`

## 🎯 CTA Trial Immédiat

**Formulaire trial-14d.html**:
- Capture: email + plan (starter/pro) + source
- Endpoint: `POST https://watch.arkforge.fr/api/trial-14d/signup`
- Payload: `{email, source, plan, campaign: 'trial_14d'}`
- No credit card required
- 14-day full access

## 🔗 Navigation

**Demo → Pricing → Trial**:
```
demo.html 
  ├─ Header: "Pricing" → /pricing.html
  ├─ Header: "Start Free Trial" → /trial-14d.html
  └─ CTA: "View Pricing →" → /pricing.html

pricing.html
  ├─ Starter CTA → /trial-14d.html?plan=starter
  ├─ Pro CTA → /trial-14d.html?plan=pro
  └─ Enterprise CTA → mailto:contact@arkforge.fr

trial-14d.html
  └─ Capture email + plan → API signup
```

## ✨ Optimisations CRO

1. **Badge "Most Popular"** sur Pro plan
2. **Social proof**: Risk-Free Trial, Stripe secure checkout
3. **FAQ section**: 7 questions couvrant objections
4. **Comparison table**: Visual des différences
5. **Mobile responsive**: Grid adaptatif
6. **No CC required**: Highlighted 3x

## 📊 Tracking

- Analytics: Plausible + custom tracking
- Events tracked:
  - `pricing_pageview`
  - `pricing_cta_click_starter`
  - `pricing_cta_click_pro`
  - `pricing_cta_click_enterprise`
  - `trial_14d_signup_attempt`
  - `trial_14d_signup_success`

## 🚀 Intégration Stripe

**État actuel**: Formulaire capture email → API backend
**Prochaine étape**: Backend doit créer Stripe checkout session avec:
- `price_id_starter` pour plan Starter
- `price_id_pro` pour plan Pro
- Trial period: 14 days
- No payment method required during trial

## 📝 Fichiers Modifiés

1. `/var/www/arkforge/pricing.html` (déployé)
2. `/var/www/arkforge/demo.html` (liens corrigés)
3. `/var/www/arkforge/trial-14d.html` (ajout param plan)

## ✅ Tests de Validation

```bash
# Pricing accessible
curl -I https://arkforge.fr/pricing.html
# → 200 OK ✓

# Trial accessible
curl -I https://arkforge.fr/trial-14d.html
# → 200 OK ✓

# Liens corrects
curl -s https://arkforge.fr/pricing.html | grep "trial-14d.html?plan="
# → 2 liens (starter + pro) ✓

# 3 plans visibles
curl -s https://arkforge.fr/pricing.html | grep -E "€29|€99|Custom"
# → 3 occurrences ✓
```

## 🎯 Objectif Métier

**Conversion visiteurs → revenus sous 48h**:
- Visiteurs demo.html → pricing.html (découverte)
- pricing.html → trial-14d.html (intention)
- trial-14d.html → signup (conversion)
- Email avec onboarding (activation)
- J+14: proposition upgrade Stripe (revenus)

## 📈 Métriques Attendues

- Taux visite pricing: 20-30% depuis demo
- Taux clic CTA trial: 10-15% sur pricing
- Taux signup trial: 40-50% sur trial page
- **Objectif**: 1er revenu sous 48h

## ✅ Statut

**DÉPLOYÉ EN PRODUCTION** - 2026-02-09 17:36 UTC

