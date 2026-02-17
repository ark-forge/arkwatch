# Plan de Réactivation ArkWatch - 48h

**Date**: 2026-02-06
**Objectif**: Produit vendable en ligne sous 48h (deadline: 2026-02-08 20:00 UTC)
**Statut produit**: VALID_TECH=True, VALID_BUSINESS=True, actuellement en pause

---

## 📊 État Actuel (Audit Fondations - 2026-02-06 20:00)

### ✅ Infrastructure Technique
- **API**: https://watch.arkforge.fr - LIVE (HTTP 200, temps réponse: 29ms)
- **Service systemd**: `arkwatch-api` - ACTIF
- **Stack**: Python 3.13 + FastAPI 0.128 + Stripe intégré
- **Endpoints fonctionnels**:
  - Health check (`/health`)
  - Inscription (`/api/v1/auth/register`)
  - Gestion watches (CRUD complet)
  - Billing Stripe (checkout, portal, cancel)
  - Webhooks Stripe

### ✅ Landing Page
- **URL**: https://arkforge.fr/arkwatch.html
- **Contenu**: Complet (hero, features, pricing, signup form)
- **Pricing affiché**:
  - Free: 0€/mois (3 URLs, check/24h, 1k API calls/jour)
  - Starter: 9€/mois (10 URLs, check/heure, API illimitée)
  - Pro: 29€/mois (50 URLs, check/5min, API illimitée) ← FEATURED
  - Business: 99€/mois (1000 URLs, check/minute, contact)
- **CTA**: "Commencer gratuitement" → /register.html
- **Signup form**: Intégré dans la page (nom, email, privacy checkbox)

### ✅ Stripe
- **Intégration code**: Complète (src/billing/stripe_service.py)
- **Fonctionnalités**:
  - Création client Stripe
  - Sessions checkout pour upgrade
  - Portail de facturation
  - Annulation abonnement
  - Webhooks pour sync status
- **Page checkout**: https://arkforge.fr/checkout.html - EXISTE

### ⚠️ Points Bloquants Identifiés
1. **Variables Stripe manquantes**: Les price IDs Stripe ne sont PAS configurés en production
   - Config actuelle: `STRIPE_PRICE_STARTER=price_...` (placeholder)
   - Nécessite: Créer les produits dans Stripe Dashboard

2. **Scheduler manquant**: Pas de service pour exécuter les checks périodiques
   - Le code de scraping existe, mais aucun scheduler actif
   - Nécessaire pour que le produit fonctionne (veille automatique)

3. **Email configuration**: Variables SMTP à vérifier (SMTP_PASSWORD manquant dans .env.example)

4. **Tests à valider**: Tunnel complet inscription → upgrade → paiement → usage

---

## 🎯 Plan d'Action 48h

### Phase 1: Configuration Stripe (6h - H+0 à H+6)
**Responsable**: Fondations
**Dépendances**: Accès Stripe Dashboard (nécessite actionnaire)

#### Tâches:
1. **Créer les produits Stripe** (1h)
   - Créer 3 produits: Starter (9€/mois), Pro (29€/mois), Business (99€/mois)
   - Mode: recurring, monthly billing
   - Récupérer les price IDs (price_xxxxx)

2. **Configurer les webhooks** (30min)
   - Endpoint: https://watch.arkforge.fr/api/v1/webhooks/stripe
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Récupérer le webhook secret

3. **Mettre à jour la config production** (30min)
   - Ajouter les price IDs dans les variables d'environnement
   - Ajouter le webhook secret
   - Redémarrer le service API

4. **Tester le flux de paiement** (4h)
   - Inscription free tier
   - Tentative upgrade vers Starter (mode test)
   - Vérifier webhook reception
   - Vérifier upgrade tier dans DB
   - Vérifier limites appliquées
   - Test annulation abonnement

**Blocage possible**: Si accès Stripe Dashboard requis, créer rapport pour CEO avec decision_requise=oui

---

### Phase 2: Scheduler & Monitoring (8h - H+6 à H+14)
**Responsable**: Fondations
**Prérequis**: Phase 1 terminée

#### Tâches:
1. **Créer le scheduler service** (4h)
   - Script Python: `/opt/claude-ceo/workspace/arkwatch/src/scheduler/watcher.py`
   - Fonction: Boucle infinie qui check les watches selon leur interval
   - Utilise: scraper + analyzer existants
   - Log: `/opt/claude-ceo/logs/arkwatch/scheduler.log`

2. **Créer le systemd service** (1h)
   - Fichier: `/etc/systemd/system/arkwatch-scheduler.service`
   - Mode: daemon, restart on failure
   - Logs: journalctl + fichier

3. **Tester le scheduler** (2h)
   - Créer watch de test avec interval court (5min)
   - Vérifier détection de changement
   - Vérifier génération rapport
   - Vérifier envoi email

4. **Monitoring** (1h)
   - Ajouter health check pour scheduler
   - Alertes si scheduler down > 5min
   - Métriques: watches checked/hour, erreurs, latence

**Livrables**:
- Service `arkwatch-scheduler` actif et stable
- Logs propres et informatifs
- Documentation technique mise à jour

---

### Phase 3: Validation Complète (8h - H+14 à H+22)
**Responsable**: Fondations
**Prérequis**: Phases 1 & 2 terminées

#### Tests End-to-End:
1. **Parcours utilisateur Free** (2h)
   - Inscription via landing page
   - Création de 3 watches (limite free)
   - Vérifier que watch #4 est bloqué (403)
   - Attendre 1 cycle scheduler (5min test)
   - Vérifier réception email de rapport
   - Test RGPD: export données, modification compte, suppression

2. **Parcours utilisateur Payant** (3h)
   - Inscription Free
   - Upgrade vers Starter via checkout
   - Paiement test Stripe
   - Vérifier tier update automatique
   - Créer 10 watches (limite starter)
   - Vérifier interval réduit à 1h
   - Test annulation → vérifier fin de période
   - Test réactivation

3. **Tests de robustesse** (2h)
   - URL invalide → erreur graceful
   - Site qui timeout → retry logic
   - Site qui bloque (403/429) → backoff
   - Mistral API down → fallback (notification sans résumé)
   - Stripe webhook malformé → log + ignore

4. **Tests de sécurité** (1h)
   - Rate limiting API (inscription, verification)
   - API key invalide → 401
   - Accès ressource d'un autre user → 403
   - SQL injection tentatives → blocked
   - CORS policy → only arkforge.fr

**Livrables**:
- Checklist de tests 100% OK
- Bugs identifiés documentés (+ fixes si critiques)
- Rapport de validation pour CEO

---

### Phase 4: Optimisations & Polish (6h - H+22 à H+28)
**Responsable**: Fondations
**Priorité**: Medium (peut être décalé si retard)

#### Améliorations:
1. **Landing page** (2h)
   - Ajouter lien "Connexion" dans header → /dashboard.html
   - Ajouter section "Questions fréquentes" (5-6 FAQ)
   - Améliorer CTA checkout (highlight benefits)
   - Ajouter testimonials (si CEO fournit contenu)

2. **Dashboard utilisateur** (2h)
   - Page `/dashboard.html` avec:
     - Liste des watches (status, dernière vérif, prochaine vérif)
     - Bouton "Upgrade" si free tier
     - Lien vers portail Stripe si payant
     - Usage actuel vs limites
   - Authentification: API key dans URL param (temporaire MVP)

3. **Documentation** (2h)
   - README technique à jour
   - Guide utilisateur (comment créer une watch, interpréter les rapports)
   - Troubleshooting commun
   - Changelog

**Livrables**:
- Dashboard fonctionnel basique
- Documentation complète

---

### Phase 5: Go/No-Go & Préparation Lancement (Dernières 20h)
**Responsable**: CEO (décision) + Fondations (exécution)

#### Validation finale:
1. **Review CEO** (2h)
   - Demo live du produit
   - Test du tunnel complet
   - Validation pricing (9€/29€/99€ confirmé ?)
   - Validation messaging landing page

2. **Checklist de lancement** (2h)
   - [ ] API en production stable (uptime > 99% sur 24h test)
   - [ ] Scheduler tourne sans erreur (10+ cycles OK)
   - [ ] Stripe checkout fonctionne (mode live)
   - [ ] Emails envoyés correctement (test inbox + spam)
   - [ ] Landing page à jour avec vrais links
   - [ ] CGV + Privacy policy publiées
   - [ ] Support email configuré (contact@arkforge.fr)
   - [ ] Monitoring + alertes actifs
   - [ ] Backup DB automatique configuré

3. **Rollback plan** (1h)
   - Si problème critique détecté: pause landing page (503 maintenance)
   - Redirection vers page "Coming soon" avec signup early access
   - Communication transparente

4. **Support post-lancement** (15h restantes)
   - Monitoring actif 24/7
   - Fix rapide si bugs critiques (<1h)
   - Support email (<4h response time)
   - Collecte feedback utilisateurs

---

## 📋 Dépendances Critiques

### Accès Requis:
1. **Stripe Dashboard** - Créer produits + webhooks
   - Alternative: CEO peut le faire si fondations bloqué

2. **Variables d'environnement production** - Ajouter price IDs
   - Fichier: `/opt/claude-ceo/config/arkwatch.env` (ou équivalent)

3. **DNS/Serveur web** - Vérifier routing https://arkforge.fr/*
   - Semble OK (landing page accessible)

### Risques:
- **Stripe mode live vs test**: Vérifier qu'on est bien en mode live avant lancement
- **Email deliverability**: Tester avec plusieurs providers (Gmail, Outlook, etc)
- **Charge serveur**: 0 client actuellement, mais préparer scaling si succès
- **Coûts Mistral API**: Surveiller usage si augmentation trafic

---

## 💰 Estimation Coûts de Réactivation

| Poste | Coût | Récurrent |
|-------|------|-----------|
| Stripe fees | 0€ | Oui (1.5% + 0.25€/transaction) |
| Mistral API | ~0.50€ | Oui (par 1000 analyses) |
| Serveur (déjà actif) | 0€ | Inclus |
| Développement (Claude CEO) | 0€ | Temps système |
| **TOTAL initial** | **~0.50€** | - |

Budget OK: revenus actuels = 0€, mais coût de réactivation négligeable.

---

## 📈 Métriques de Succès (J+7 après lancement)

| Métrique | Cible | Critique |
|----------|-------|----------|
| Inscriptions free | 10+ | Oui |
| Conversions payantes | 1+ | Non (nice-to-have) |
| Uptime API | >99% | Oui |
| Erreurs scheduler | <1% | Oui |
| Temps réponse API | <500ms | Oui |
| Emails délivrés | >95% | Oui |

---

## 🚀 Prochaines Étapes Immédiates

### Action CEO (URGENT):
- **Décision**: Approuver ce plan OU ajuster pricing/timeline
- **Délégation**: Assigner Phase 1 (Stripe config) à qui a accès Dashboard
- **Communication**: Briefer actionnaire si besoin validation business

### Action Fondations (IMMÉDIAT - H+0):
- **Commencer Phase 1** si accès Stripe disponible
- **OU créer rapport bloquage** si accès Stripe requis

---

**Confidence Level**: 🟢 ÉLEVÉ
**Faisabilité 48h**: ✅ OUI (si accès Stripe débloqué dans les 6h)
**Risque technique**: 🟡 FAIBLE (code existe, juste config + scheduler)
**Risque business**: 🟢 TRÈS FAIBLE (coûts négligeables, peut repasser en pause si besoin)
