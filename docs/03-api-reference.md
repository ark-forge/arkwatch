# ArkWatch - API Reference

**Base URL** : `https://watch.arkforge.fr`

**Authentification** : Header `X-API-Key: ak_votre_cle`

**Format** : JSON (Content-Type: application/json)

---

## Endpoints publics

### GET /

Informations sur l'API.

**Réponse** (200) :

```json
{
  "name": "ArkWatch API",
  "version": "0.1.0",
  "status": "running"
}
```

### GET /health

Vérification de l'état de l'API.

**Réponse** (200) :

```json
{
  "status": "healthy"
}
```

### GET /ready

Vérification que l'API est prête à recevoir des requêtes.

**Réponse** (200) :

```json
{
  "status": "ready"
}
```

### GET /privacy

Politique de confidentialité (RGPD Art. 13/14). Retourne du texte Markdown.

---

## Authentification

### POST /api/v1/auth/register

Créer un compte et obtenir une clé API.

**Rate limit** : 3 par IP par heure

**Body** :

| Champ | Type | Requis | Description |
|---|---|---|---|
| `email` | string | oui | Adresse email valide (max 254 caractères) |
| `name` | string | oui | Nom (2-100 caractères) |
| `privacy_accepted` | boolean | oui | Doit être `true` |

**Réponse** (201) :

```json
{
  "api_key": "ak_...",
  "email": "user@example.com",
  "name": "User Name",
  "tier": "free",
  "message": "Welcome! A verification code has been sent to your email...",
  "privacy_policy": "https://arkforge.fr/privacy"
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 400 | Paramètres invalides |
| 409 | Email déjà enregistré |
| 429 | Rate limit dépassé |

---

### POST /api/v1/auth/verify-email

Vérifier l'adresse email avec le code reçu.

**Rate limit** : 5 tentatives par email par 15 minutes

**Body** :

| Champ | Type | Requis | Description |
|---|---|---|---|
| `email` | string | oui | Adresse email |
| `code` | string | oui | Code à 6 chiffres |

**Réponse** (200) :

```json
{
  "status": "verified",
  "message": "Email verified successfully. You can now use all API features."
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 400 | Code invalide ou expiré |
| 429 | Trop de tentatives |

Le code expire après 24 heures.

---

### POST /api/v1/auth/resend-verification

Renvoyer le code de vérification.

**Rate limit** : 3 par IP par heure

**Body** :

| Champ | Type | Requis | Description |
|---|---|---|---|
| `email` | string | oui | Adresse email |

**Réponse** (200) :

```json
{
  "status": "sent",
  "message": "If this email is registered and unverified, a new code has been sent."
}
```

Retourne toujours 200 pour éviter l'énumération d'emails.

---

### PATCH /api/v1/auth/account

Mettre à jour les informations du compte (RGPD Art. 16).

**Auth requise** : oui + email vérifié

**Body** :

| Champ | Type | Requis | Description |
|---|---|---|---|
| `name` | string | non | Nouveau nom (2-100 caractères) |

**Réponse** (200) :

```json
{
  "status": "updated",
  "updated_fields": ["name"],
  "message": "Account information updated successfully (GDPR Art. 16)."
}
```

---

### DELETE /api/v1/auth/account

Supprimer le compte et toutes les données associées (RGPD Art. 17).

**Auth requise** : oui

Supprime en cascade : watches, rapports, clé API, abonnement Stripe.

**Réponse** (200) :

```json
{
  "status": "deleted",
  "email": "user@example.com",
  "data_deleted": true,
  "stripe_subscription_cancelled": false,
  "message": "Your account and all associated data have been permanently deleted."
}
```

---

### GET /api/v1/auth/account/data

Exporter toutes les données personnelles (RGPD Art. 15).

**Auth requise** : oui

**Réponse** (200) :

```json
{
  "account": {
    "email": "user@example.com",
    "name": "User Name",
    "tier": "free",
    "created_at": "2026-02-06T10:00:00",
    "requests_count": 5,
    "privacy_accepted_at": "2026-02-06T10:00:00"
  },
  "watches": [],
  "reports": [],
  "privacy_policy": "https://arkforge.fr/privacy",
  "message": "This is all the data we hold about you (GDPR Art. 15)."
}
```

---

### GET /api/v1/auth/unsubscribe

Se désinscrire des notifications email (RGPD Art. 21).

**Query parameters** :

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `email` | string | oui | Adresse email |
| `token` | string | oui | Token HMAC de désinscription |

**Réponse** (200) :

```json
{
  "status": "unsubscribed",
  "watches_updated": 5,
  "message": "You have been unsubscribed from all email notifications..."
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 400 | Token invalide ou expiré |

---

## Watches

Tous les endpoints watches nécessitent une authentification et un email vérifié.

### POST /api/v1/watches

Créer un nouveau watch.

**Body** :

| Champ | Type | Requis | Description |
|---|---|---|---|
| `url` | string | oui | URL HTTPS à surveiller |
| `name` | string | oui | Nom du watch |
| `check_interval` | integer | non | Intervalle en secondes (défaut: 3600) |
| `notify_email` | string | non | Email d'alerte (défaut: email du compte) |
| `min_change_ratio` | float | non | Seuil de changement 0.0-1.0 (défaut: 0.05) |

**Réponse** (201) :

```json
{
  "id": "uuid",
  "user_email": "user@example.com",
  "name": "Mon Watch",
  "url": "https://example.com",
  "check_interval": 86400,
  "min_change_ratio": 0.05,
  "notify_email": "user@example.com",
  "status": "active",
  "last_check": null,
  "created_at": "2026-02-06T10:00:00",
  "updated_at": "2026-02-06T10:00:00"
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 400 | URL non autorisée (IP privée, format invalide) |
| 403 | Limite de watches atteinte pour votre plan |

---

### GET /api/v1/watches

Lister tous vos watches.

**Query parameters** :

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `status` | string | non | Filtrer par statut : `active`, `paused`, `error` |

**Réponse** (200) :

```json
[
  {
    "id": "uuid",
    "name": "Mon Watch",
    "url": "https://example.com",
    "check_interval": 86400,
    "status": "active",
    "last_check": "2026-02-06T09:00:00",
    "created_at": "2026-02-06T08:00:00"
  }
]
```

---

### GET /api/v1/watches/{watch_id}

Obtenir les détails d'un watch.

**Réponse** (200) :

```json
{
  "id": "uuid",
  "name": "Mon Watch",
  "url": "https://example.com",
  "check_interval": 86400,
  "status": "active",
  "last_check": "2026-02-06T09:00:00",
  "last_content_hash": "sha256..."
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 404 | Watch non trouvé |
| 403 | Accès refusé |

---

### PATCH /api/v1/watches/{watch_id}

Modifier un watch.

**Body** (tous les champs sont optionnels) :

| Champ | Type | Description |
|---|---|---|
| `name` | string | Nouveau nom |
| `check_interval` | integer | Nouvel intervalle (secondes) |
| `notify_email` | string | Nouvel email d'alerte |
| `status` | string | `active`, `paused` |
| `min_change_ratio` | float | Nouveau seuil (0.0-1.0) |

**Réponse** (200) : le watch mis à jour.

**Erreurs** :

| Code | Cause |
|---|---|
| 404 | Watch non trouvé |
| 403 | Accès refusé |

---

### DELETE /api/v1/watches/{watch_id}

Supprimer un watch et tous ses rapports.

**Réponse** (200) :

```json
{
  "status": "deleted"
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 404 | Watch non trouvé |
| 403 | Accès refusé |

---

## Reports

### GET /api/v1/reports

Lister les rapports.

**Query parameters** :

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `watch_id` | string | non | Filtrer par watch |
| `limit` | integer | non | Nombre maximum de résultats (défaut: 100) |

**Réponse** (200) :

```json
[
  {
    "id": "uuid",
    "watch_id": "uuid",
    "changes_detected": true,
    "diff": "...",
    "ai_summary": "Le prix du produit a augmenté de 29€ à 39€.",
    "ai_importance": "high",
    "notified": true,
    "created_at": "2026-02-06T09:00:00"
  }
]
```

---

### GET /api/v1/reports/{report_id}

Obtenir les détails d'un rapport.

**Réponse** (200) :

```json
{
  "id": "uuid",
  "watch_id": "uuid",
  "changes_detected": true,
  "previous_hash": "sha256...",
  "current_hash": "sha256...",
  "diff": "...",
  "ai_summary": "...",
  "ai_importance": "high",
  "notified": true,
  "created_at": "2026-02-06T09:00:00"
}
```

**Erreurs** :

| Code | Cause |
|---|---|
| 404 | Rapport non trouvé |
| 403 | Accès refusé |

---

## Billing (Facturation)

### GET /api/v1/billing/subscription

Obtenir l'état de l'abonnement.

**Auth requise** : oui

**Réponse** (200) :

```json
{
  "tier": "starter",
  "status": "active",
  "current_period_end": "2026-03-06T10:00:00",
  "cancel_at_period_end": false,
  "stripe_customer_id": "cus_..."
}
```

---

### POST /api/v1/billing/checkout

Créer une session de paiement Stripe pour upgrader.

**Auth requise** : oui

**Body** :

| Champ | Type | Requis | Description |
|---|---|---|---|
| `tier` | string | oui | `starter`, `pro`, ou `business` |
| `success_url` | string | non | URL de redirection après paiement |
| `cancel_url` | string | non | URL de redirection si annulation |

**Réponse** (200) :

```json
{
  "session_id": "cs_...",
  "checkout_url": "https://checkout.stripe.com/pay/..."
}
```

---

### POST /api/v1/billing/portal

Accéder au portail de gestion Stripe (factures, moyens de paiement).

**Auth requise** : oui

**Réponse** (200) :

```json
{
  "portal_url": "https://billing.stripe.com/..."
}
```

---

### POST /api/v1/billing/cancel

Annuler l'abonnement (effectif en fin de période).

**Auth requise** : oui

**Réponse** (200) :

```json
{
  "message": "Subscription will be cancelled at the end of the billing period",
  "cancel_at_period_end": true
}
```

---

### GET /api/v1/billing/usage

Consulter l'utilisation par rapport aux limites du plan.

**Auth requise** : oui

**Réponse** (200) :

```json
{
  "tier": "starter",
  "watches_used": 5,
  "watches_limit": 10,
  "check_interval_min": 3600,
  "subscription_status": "active"
}
```

---

## Plans et tarifs

| Plan | Watches | Intervalle min | Prix mensuel |
|---|---|---|---|
| **Free** | 3 | 24h (86400s) | Gratuit |
| **Starter** | 10 | 1h (3600s) | Voir site |
| **Pro** | 50 | 5min (300s) | Voir site |
| **Business** | 1000 | 1min (60s) | Voir site |

---

## Codes d'erreur

Toutes les erreurs suivent le format :

```json
{
  "detail": "Description de l'erreur"
}
```

| Code | Signification |
|---|---|
| 400 | Requête invalide (paramètres manquants ou incorrects) |
| 401 | Non authentifié (clé API manquante ou invalide) |
| 403 | Accès interdit (pas propriétaire, limite dépassée, email non vérifié) |
| 404 | Ressource non trouvée |
| 409 | Conflit (email déjà enregistré) |
| 429 | Trop de requêtes (rate limit) |
| 500 | Erreur interne du serveur |

---

## Rate Limiting

| Endpoint | Limite | Fenêtre |
|---|---|---|
| `POST /auth/register` | 3 par IP | 1 heure |
| `POST /auth/verify-email` | 5 par email | 15 minutes |
| `POST /auth/resend-verification` | 3 par IP | 1 heure |

Lorsqu'un rate limit est atteint, l'API retourne un code 429.
