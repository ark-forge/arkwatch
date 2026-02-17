# Checklist Réactivation ArkWatch

**Date**: 6 février 2026
**Objectif**: Produit vendable en ligne sous 48h

---

## 📋 Phase 1: Configuration Stripe (ACTIONNAIRE)

### Étape 1.1: Créer les produits Stripe
- [ ] Se connecter à https://dashboard.stripe.com
- [ ] Aller dans **Produits** → **Créer un produit**
- [ ] Créer **ArkWatch Starter**
  - Prix: 4.90€/mois (ou décision CEO)
  - Récurrent: Mensuel
  - Devise: EUR
  - Noter le Price ID: `price_________________`
- [ ] Créer **ArkWatch Pro**
  - Prix: 9.00€/mois
  - Récurrent: Mensuel
  - Devise: EUR
  - Noter le Price ID: `price_________________`
- [ ] Créer **ArkWatch Business**
  - Prix: 29.00€/mois
  - Récurrent: Mensuel
  - Devise: EUR
  - Noter le Price ID: `price_________________`

### Étape 1.2: Récupérer les clés API
- [ ] Aller dans **Développeurs** → **Clés API**
- [ ] Activer le mode **LIVE** (toggle en haut)
- [ ] Copier **Clé secrète**: `sk_live_____________________________`
- [ ] Copier **Clé publiable**: `pk_live_____________________________`

### Étape 1.3: Configurer le webhook
- [ ] Aller dans **Développeurs** → **Webhooks**
- [ ] Cliquer **Ajouter un endpoint**
- [ ] URL: `https://watch.arkforge.fr/api/v1/webhooks/stripe`
- [ ] Événements à écouter:
  - [ ] `checkout.session.completed`
  - [ ] `customer.subscription.created`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
  - [ ] `invoice.payment_succeeded`
  - [ ] `invoice.payment_failed`
- [ ] Copier **Signing secret**: `whsec_____________________________`

### Étape 1.4: Créer le fichier .env
- [ ] Se connecter au serveur: `ssh ubuntu@vps-ac247687-vps-ovh-net`
- [ ] Créer le fichier: `nano /opt/claude-ceo/workspace/arkwatch/config/.env`
- [ ] Copier le template ci-dessous et remplir les valeurs

```bash
# API Configuration
API_BASE_URL=https://watch.arkforge.fr
APP_URL=https://arkforge.fr

# Stripe LIVE Keys
STRIPE_SECRET_KEY=sk_live_____________________________
STRIPE_PUBLISHABLE_KEY=pk_live_____________________________
STRIPE_WEBHOOK_SECRET=whsec_____________________________

# Stripe Price IDs
STRIPE_PRICE_STARTER=price_________________
STRIPE_PRICE_PRO=price_________________
STRIPE_PRICE_BUSINESS=price_________________

# Stripe Settings
STRIPE_CURRENCY=eur
STRIPE_STATEMENT_DESCRIPTOR=ArkWatch

# Email
SMTP_FROM=noreply@arkforge.fr
```

- [ ] Sauvegarder: `Ctrl+X`, puis `Y`, puis `Enter`
- [ ] Vérifier les permissions: `chmod 600 /opt/claude-ceo/workspace/arkwatch/config/.env`

### Étape 1.5: Redémarrer le service
- [ ] Redémarrer: `sudo systemctl restart arkwatch-api`
- [ ] Vérifier le statut: `sudo systemctl status arkwatch-api`
- [ ] Vérifier les logs: `sudo journalctl -u arkwatch-api -n 50`
- [ ] Tester l'API: `curl https://watch.arkforge.fr/health`

**✅ Phase 1 terminée** → Informer le CEO

---

## 📋 Phase 2: Landing Page (FONDATIONS)

### Étape 2.1: Backup de la landing actuelle
- [ ] `cp /var/www/arkforge/arkwatch.html /var/www/arkforge/arkwatch.html.backup_20260206`

### Étape 2.2: Ajouter les boutons d'achat
- [ ] Éditer `/var/www/arkforge/arkwatch.html`
- [ ] Localiser les 3 pricing cards (Free, Pro, Business)
- [ ] Remplacer les boutons statiques par des boutons avec `onclick="subscribeTier('...')"`
- [ ] Ajouter le script JavaScript de gestion Stripe Checkout (voir plan détaillé)

### Étape 2.3: Créer la page de succès
- [ ] Créer le dossier: `mkdir -p /var/www/arkforge/arkwatch`
- [ ] Créer le fichier: `/var/www/arkforge/arkwatch/success.html`
- [ ] Copier le template de success.html (voir plan détaillé)

### Étape 2.4: Vérifier l'accès
- [ ] Tester: `curl -I https://arkforge.fr/arkwatch.html`
- [ ] Tester: `curl -I https://arkforge.fr/arkwatch/success.html`
- [ ] Purger le cache Nginx: `sudo nginx -s reload`

**✅ Phase 2 terminée** → Passer à Phase 3

---

## 📋 Phase 3: Tests (FONDATIONS)

### Étape 3.1: Test en mode TEST Stripe
- [ ] Ouvrir https://arkforge.fr/arkwatch.html dans un navigateur
- [ ] Cliquer sur "S'abonner - 9€/mois" (Plan Pro)
- [ ] Entrer email test: `test+arkwatch@example.com`
- [ ] Entrer nom test: `Test User`
- [ ] Sur la page Stripe Checkout:
  - Email: `test+arkwatch@example.com`
  - Carte: `4242 4242 4242 4242`
  - Date: `12/34`
  - CVC: `123`
- [ ] Valider le paiement
- [ ] Vérifier la redirection vers success.html
- [ ] Vérifier l'email de confirmation reçu

### Étape 3.2: Vérifier les webhooks
- [ ] Pendant le test, monitorer les logs:
  ```bash
  sudo journalctl -u arkwatch-api -f | grep -i webhook
  ```
- [ ] Vérifier que `checkout.session.completed` est reçu
- [ ] Vérifier que le tier de l'utilisateur est mis à jour

### Étape 3.3: Tester le portail de facturation
- [ ] Récupérer la clé API de test dans les logs ou localStorage
- [ ] Tester l'endpoint:
  ```bash
  curl -X POST https://watch.arkforge.fr/api/v1/billing/portal \
    -H "X-API-Key: YOUR_TEST_KEY"
  ```
- [ ] Vérifier la redirection vers le portail Stripe

### Étape 3.4: Documenter les résultats
- [ ] Créer `/opt/claude-ceo/workspace/arkwatch/tests/TUNNEL_PAIEMENT_TEST_RESULTS.md`
- [ ] Noter les résultats de chaque test
- [ ] Capturer les screenshots si problème
- [ ] Lister les bugs trouvés

**✅ Phase 3 terminée** → Informer le CEO

---

## 📋 Phase 4: Production LIVE (CEO)

### Étape 4.1: Checklist pré-lancement
- [ ] Clés Stripe LIVE configurées dans `.env`
- [ ] Produits Stripe créés avec vrais prix
- [ ] Webhook Stripe configuré et testé
- [ ] Landing page mise à jour avec boutons
- [ ] Page success.html créée
- [ ] Tests tunnel complet passés en mode TEST
- [ ] CGV à jour avec prix finaux
- [ ] Email de confirmation testé
- [ ] Monitoring en place

### Étape 4.2: Basculer en LIVE
- [ ] Backup: `cp /opt/claude-ceo/workspace/arkwatch/config/.env /opt/claude-ceo/workspace/arkwatch/config/.env.test.backup`
- [ ] Vérifier que les clés dans `.env` sont bien en mode LIVE (sk_live_...)
- [ ] Redémarrer: `sudo systemctl restart arkwatch-api`
- [ ] Vérifier: `curl https://watch.arkforge.fr/health`
- [ ] Monitorer les logs: `sudo journalctl -u arkwatch-api -f`

### Étape 4.3: Test de smoke en LIVE
- [ ] Créer un compte test réel avec un email réel
- [ ] Essayer d'acheter le plan Starter avec une vraie carte
- [ ] **IMPORTANT**: Annuler immédiatement l'abonnement après validation
- [ ] Vérifier le webhook reçu dans les logs
- [ ] Vérifier l'email envoyé
- [ ] Vérifier la facturation dans Stripe Dashboard

**✅ Phase 4 terminée** → ArkWatch est LIVE 🎉

---

## 🎯 Validation Finale

### Tests post-lancement
- [ ] API Health: `https://watch.arkforge.fr/health` → 200 OK
- [ ] Landing accessible: `https://arkforge.fr/arkwatch.html`
- [ ] Boutons d'achat visibles et cliquables
- [ ] Redirection Stripe Checkout fonctionne
- [ ] Paiement accepté et traité
- [ ] Email de confirmation envoyé
- [ ] Tier utilisateur mis à jour
- [ ] Portail de facturation accessible

### Monitoring continu
- [ ] Configurer alerte sur échecs webhook > 3
- [ ] Configurer alerte sur downtime API > 5 min
- [ ] Vérifier les logs quotidiennement pendant 7 jours
- [ ] Surveiller les premiers paiements réels

---

## 📊 Métriques de Succès

**Jour 1**:
- [ ] 0 erreur critique
- [ ] 0 downtime API
- [ ] 100% webhooks reçus

**Semaine 1**:
- [ ] Premier paiement réel reçu
- [ ] 0 remboursement
- [ ] Uptime > 99%

**Mois 1**:
- [ ] 10+ utilisateurs payants
- [ ] Revenus > 50€
- [ ] NPS > 7/10

---

## 🚨 Plan B si Problème

### Si Stripe bloque
- [ ] Contacter support Stripe: support@stripe.com
- [ ] Fournir SIRET: 488 010 331 00020
- [ ] Expliquer le business: surveillance web IA

### Si webhook ne marche pas
- [ ] Vérifier la signature dans les logs
- [ ] Tester manuellement: Stripe Dashboard → Webhooks → Send test webhook
- [ ] Créer endpoint `/api/v1/billing/sync` pour resynchroniser

### Si email non reçu
- [ ] Vérifier config msmtp: `cat /etc/msmtprc`
- [ ] Tester manuellement: `echo "test" | msmtp test@example.com`
- [ ] Afficher la clé API sur success.html en backup

---

**Document créé par**: Worker Fondations
**Date**: 6 février 2026
**Status**: PRÊT À EXÉCUTER
