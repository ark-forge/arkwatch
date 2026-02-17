# Guide Actionnaire - Configuration Stripe pour ArkWatch

**Durée estimée**: 30 minutes
**Objectif**: Activer les paiements en ligne pour ArkWatch
**Prérequis**: Compte Stripe (si pas encore créé → https://dashboard.stripe.com/register)

---

## 🎯 Ce que vous devez faire

Configurer Stripe pour qu'ArkWatch puisse accepter des paiements par carte bancaire.

**Résultat attendu**: 3 produits créés + clés API récupérées + webhook configuré

---

## 📝 Étape 1: Se Connecter à Stripe (2 min)

1. Aller sur https://dashboard.stripe.com
2. Se connecter avec votre compte
3. **IMPORTANT**: Basculer en mode **LIVE** (toggle en haut à droite de l'écran)
   - Si vous voyez "Mode test", cliquez dessus pour passer en "Mode LIVE"
   - Les clés en mode test ne fonctionnent pas pour de vrais paiements

---

## 📦 Étape 2: Créer les 3 Produits (15 min)

### Produit 1: ArkWatch Starter

1. Dans le menu de gauche, cliquer sur **Produits**
2. Cliquer sur **+ Créer un produit**
3. Remplir:
   - **Nom**: `ArkWatch Starter`
   - **Description**: `Plan Starter - 10 URLs surveillées, vérification toutes les heures`
   - **Prix**: `4.90` EUR (ou autre montant selon décision CEO)
   - **Type de facturation**: `Récurrent`
   - **Fréquence**: `Mensuel`
4. Cliquer sur **Enregistrer le produit**
5. **IMPORTANT**: Noter le **Price ID** (format `price_XXXXXXXXXXXXX`)
   - Il apparaît dans l'URL ou dans les détails du prix
   - Exemple: `price_1QfFpF2L4x3y0z9a123456`
   - ✍️ Notez-le ici: `STRIPE_PRICE_STARTER = price_________________`

### Produit 2: ArkWatch Pro

1. Cliquer sur **+ Créer un produit**
2. Remplir:
   - **Nom**: `ArkWatch Pro`
   - **Description**: `Plan Pro - 50 URLs surveillées, vérification toutes les 5 minutes`
   - **Prix**: `9.00` EUR
   - **Type de facturation**: `Récurrent`
   - **Fréquence**: `Mensuel`
3. Cliquer sur **Enregistrer le produit**
4. ✍️ Noter le Price ID: `STRIPE_PRICE_PRO = price_________________`

### Produit 3: ArkWatch Business

1. Cliquer sur **+ Créer un produit**
2. Remplir:
   - **Nom**: `ArkWatch Business`
   - **Description**: `Plan Business - 1000 URLs surveillées, vérification chaque minute`
   - **Prix**: `29.00` EUR
   - **Type de facturation**: `Récurrent`
   - **Fréquence**: `Mensuel`
3. Cliquer sur **Enregistrer le produit**
4. ✍️ Noter le Price ID: `STRIPE_PRICE_BUSINESS = price_________________`

---

## 🔑 Étape 3: Récupérer les Clés API (5 min)

1. Dans le menu de gauche, cliquer sur **Développeurs** → **Clés API**
2. **VÉRIFIER**: Le toggle en haut est bien sur **Mode LIVE** (et non "Mode test")
3. Copier les 2 clés:

### Clé Secrète (Secret Key)
- Cliquer sur **Afficher** dans la section "Clé secrète"
- Copier la clé (commence par `sk_live_`)
- ✍️ Notez-la ici: `STRIPE_SECRET_KEY = sk_live_____________________________`
- ⚠️ **IMPORTANT**: Ne partagez JAMAIS cette clé publiquement (email, Slack, etc.)

### Clé Publiable (Publishable Key)
- Copier la clé dans la section "Clé publiable"
- Elle commence par `pk_live_`
- ✍️ Notez-la ici: `STRIPE_PUBLISHABLE_KEY = pk_live_____________________________`

---

## 🔔 Étape 4: Configurer le Webhook (8 min)

Les webhooks permettent à Stripe d'informer ArkWatch quand un paiement est effectué.

1. Dans le menu de gauche, cliquer sur **Développeurs** → **Webhooks**
2. Cliquer sur **+ Ajouter un endpoint**
3. Remplir:
   - **URL de l'endpoint**: `https://watch.arkforge.fr/api/v1/webhooks/stripe`
   - **Description**: `ArkWatch subscription events`
4. Dans **Événements à écouter**, cliquer sur **+ Sélectionner des événements**
5. Cocher les 6 événements suivants:
   - [ ] `checkout.session.completed`
   - [ ] `customer.subscription.created`
   - [ ] `customer.subscription.updated`
   - [ ] `customer.subscription.deleted`
   - [ ] `invoice.payment_succeeded`
   - [ ] `invoice.payment_failed`
6. Cliquer sur **Ajouter des événements**
7. Cliquer sur **Ajouter un endpoint**
8. **IMPORTANT**: Cliquer sur l'endpoint que vous venez de créer
9. Copier le **Signing secret** (commence par `whsec_`)
10. ✍️ Notez-le ici: `STRIPE_WEBHOOK_SECRET = whsec_____________________________`

---

## 📋 Récapitulatif - Vos Valeurs à Fournir

Vous devez maintenant avoir noté 6 valeurs:

```
STRIPE_PRICE_STARTER = price_________________
STRIPE_PRICE_PRO = price_________________
STRIPE_PRICE_BUSINESS = price_________________
STRIPE_SECRET_KEY = sk_live_____________________________
STRIPE_PUBLISHABLE_KEY = pk_live_____________________________
STRIPE_WEBHOOK_SECRET = whsec_____________________________
```

**⚠️ SÉCURITÉ**:
- Ne partagez jamais ces valeurs par email non chiffré
- Ne les postez jamais sur Slack, Discord, ou tout chat public
- Stockez-les dans un gestionnaire de mots de passe si possible

---

## 📤 Prochaine Étape

**Fournir ces valeurs au CEO** via un canal sécurisé:

**Option A - SSH Serveur** (recommandé):
1. Se connecter au serveur: `ssh ubuntu@vps-ac247687-vps-ovh-net`
2. Éditer le fichier: `nano /opt/claude-ceo/workspace/arkwatch/config/.env`
3. Copier le template ci-dessous et remplir avec vos valeurs
4. Sauvegarder: `Ctrl+X`, puis `Y`, puis `Enter`

Template du fichier `.env`:
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

**Option B - Telegram Chiffré**:
Envoyer les 6 valeurs au CEO via Telegram (messages supprimables)

**Option C - Email Chiffré**:
Utiliser ProtonMail ou un email avec PGP

---

## ✅ Validation

Après avoir fourni les valeurs:

1. Le CEO redémarrera le service ArkWatch
2. Vous recevrez une confirmation que Stripe est bien configuré
3. Vous pourrez voir les premiers paiements test dans votre Dashboard Stripe

---

## 🆘 Aide

### "Je ne trouve pas les Price IDs"
- Aller dans **Produits**
- Cliquer sur le produit (ex: "ArkWatch Pro")
- Le Price ID est visible dans l'URL ou dans la section "Informations sur le tarif"
- Format: `price_` suivi de 14-24 caractères

### "Je ne vois pas le toggle Mode LIVE"
- En haut à droite de l'écran Stripe Dashboard
- Peut être écrit "Test" ou "Test mode"
- Cliquer dessus pour basculer en "Live"
- Si vous ne le voyez pas, votre compte n'est peut-être pas encore activé

### "Stripe me demande des informations supplémentaires"
C'est normal pour un nouveau compte. Stripe peut demander:
- Informations sur l'entreprise (SIRET, adresse)
- Pièce d'identité
- Informations bancaires pour recevoir les paiements

**SIRET ArkForge**: 488 010 331 00020
**Activité**: Services de surveillance web par IA
**Adresse**: (votre adresse d'entrepreneur individuel)

Remplissez ces informations dans **Paramètres** → **Informations commerciales**

### "Le webhook ne fonctionne pas"
- Vérifier que l'URL est exacte: `https://watch.arkforge.fr/api/v1/webhooks/stripe`
- Vérifier que vous avez bien sélectionné les 6 événements listés
- Tester le webhook: dans Stripe Dashboard → Webhooks → votre endpoint → "Envoyer un événement test"

---

## 🔐 Sécurité des Données de Paiement

**Rassurez-vous**:
- ArkWatch ne stocke AUCUNE donnée de carte bancaire
- Tous les paiements sont gérés par Stripe (conforme PCI DSS)
- Les clients saisissent leur carte directement sur les pages Stripe
- Vous pouvez consulter tous les paiements dans votre Dashboard Stripe

**Obligations légales**:
- Stripe envoie automatiquement les factures aux clients
- Vous pouvez télécharger les factures pour votre comptabilité
- Conservation légale: 10 ans (Stripe le fait automatiquement)

---

## 💰 Frais Stripe

**En Europe** (tarif standard):
- 1.5% + 0.25€ par transaction réussie
- Pas de frais d'abonnement mensuel
- Pas de frais cachés

**Exemple**:
- Client paie 9€/mois pour ArkWatch Pro
- Frais Stripe: (9€ × 1.5%) + 0.25€ = 0.39€
- Vous recevez: 9€ - 0.39€ = **8.61€**

**Versement sur votre compte**:
- Stripe verse automatiquement tous les 7 jours
- Sur le compte bancaire renseigné dans **Paramètres** → **Informations bancaires**

---

## 📞 Support

**Support Stripe**:
- Email: support@stripe.com
- Chat: Disponible dans le Dashboard (icône en bas à droite)
- Réponse moyenne: < 24h

**Support ArkForge**:
- Contacter le CEO via Telegram
- Email: apps.desiorac@gmail.com

---

**Temps total estimé**: 30 minutes
**Difficulté**: ⭐⭐☆☆☆ (Facile - aucune compétence technique requise)

Merci d'avoir configuré Stripe ! 🎉

Une fois terminé, ArkWatch pourra accepter ses premiers paiements.
