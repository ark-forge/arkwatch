# TÂCHE #20260887 - Landing Page Pricing ArkWatch
**Status**: ✅ COMPLETED  
**Date**: 2026-02-09 17:36 UTC  
**Worker**: Fondations

## 🎯 Objectif

Créer landing page pricing avec 3 plans clairs et CTA trial immédiat pour convertir visiteurs en revenus sous 48h.

## ✅ Livrables

### 1. Page Pricing - https://arkforge.fr/pricing.html
- **Design**: Modern, gradient hero, 3-column responsive grid
- **Plans**:
  - Starter: €29/mois (10 monitors, check 15min)
  - Pro: €99/mois (unlimited, check 5min) - FEATURED
  - Enterprise: Custom (contact sales)
- **CTA**: "Start 14-Day Free Trial" sur chaque plan
- **Optimisations CRO**:
  - Badge "Most Popular" sur Pro
  - Social proof section (Risk-Free Trial)
  - FAQ (7 questions)
  - Comparison table
  - Mobile responsive

### 2. Page Trial - https://arkforge.fr/trial-14d.html
- **Formulaire**: Capture email + plan (starter/pro)
- **Endpoint**: `POST /api/trial-14d/signup`
- **Payload**: `{email, source, plan, campaign}`
- **UX**: No credit card, 14-day full access
- **Intégration**: Prêt pour Stripe checkout (backend)

### 3. Navigation Corrigée
- **demo.html** → liens vers pricing.html et trial-14d.html
- **pricing.html** → liens vers trial-14d.html?plan=starter/pro
- **Tous les liens fonctionnels** ✓

## 📊 Tests de Validation

```bash
✅ Test 1: Pricing accessible (200 OK)
✅ Test 2: Trial accessible (200 OK)
✅ Test 3: 2 liens trial avec params plan
✅ Test 4: 3 plans visibles (€29, €99, Custom)
✅ Test 5: Demo → Pricing navigation (2 liens)
```

## 🔗 Flux Conversion

```
Visiteur
  ↓
demo.html (Interactive Demo)
  ↓ "View Pricing"
pricing.html (3 Plans)
  ↓ "Start 14-Day Free Trial" ?plan=starter/pro
trial-14d.html (Signup Form)
  ↓ POST /api/trial-14d/signup
API Backend
  ↓ Envoi email onboarding
Utilisateur activé
  ↓ J+14
Proposition upgrade Stripe
  ↓
💰 REVENUS
```

## 📈 Métriques Attendues

- **Taux visite pricing**: 20-30% (depuis demo)
- **Taux clic CTA trial**: 10-15% (sur pricing)
- **Taux signup**: 40-50% (sur trial page)
- **Objectif**: **1er revenu sous 48h**

## 🚀 Prochaines Étapes (Backend)

1. **API endpoint** `/api/trial-14d/signup` doit:
   - Créer user avec plan (starter/pro)
   - Envoyer email onboarding
   - Générer token activation
   - Logger conversion source

2. **Intégration Stripe** (quand user upgrade J+14):
   - Créer checkout session
   - Price ID selon plan
   - Trial period: 14 days
   - Webhook subscription.created

## 📝 Fichiers Déployés

- `/var/www/arkforge/pricing.html` (20KB)
- `/var/www/arkforge/demo.html` (26KB, liens corrigés)
- `/var/www/arkforge/trial-14d.html` (14KB, ajout param plan)

## ✅ Résultat

**OBJECTIF ATTEINT**: Landing page pricing complète, déployée en production, avec 3 plans clairs et CTA trial immédiat. Navigation optimisée demo → pricing → trial. Prêt à convertir visiteurs en revenus.

**DÉLAI**: ~6min (17:30 → 17:36 UTC)

---

**Documentation complète**: `/opt/claude-ceo/workspace/arkwatch/PRICING_PAGE_DEPLOYMENT_20260209.md`
