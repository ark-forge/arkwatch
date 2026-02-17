# ArkWatch - Quick Start Guide

Surveillez vos pages web et recevez des alertes intelligentes en 5 minutes.

## Pré-requis

- Un terminal avec `curl` (ou tout client HTTP)
- Une adresse email valide

## Etape 1 : Créer votre compte (30 secondes)

```bash
curl -X POST https://watch.arkforge.fr/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "votre@email.com",
    "name": "Votre Nom",
    "privacy_accepted": true
  }'
```

Vous recevez en retour votre clé API :

```json
{
  "api_key": "ak_abc123...",
  "tier": "free",
  "message": "Welcome! A verification code has been sent to your email..."
}
```

**Conservez précieusement votre clé API** (`ak_...`). Elle ne sera pas affichée à nouveau.

## Etape 2 : Vérifier votre email (1 minute)

Consultez votre boîte mail, récupérez le code à 6 chiffres et vérifiez :

```bash
curl -X POST https://watch.arkforge.fr/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "votre@email.com",
    "code": "123456"
  }'
```

Réponse attendue :

```json
{
  "status": "verified",
  "message": "Email verified successfully. You can now use all API features."
}
```

## Etape 3 : Créer votre premier Watch (1 minute)

Remplacez `ak_VOTRE_CLE` par votre clé API :

```bash
curl -X POST https://watch.arkforge.fr/api/v1/watches \
  -H "X-API-Key: ak_VOTRE_CLE" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "name": "Mon premier watch",
    "check_interval": 86400
  }'
```

Réponse :

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Mon premier watch",
  "url": "https://example.com",
  "status": "active",
  "check_interval": 86400
}
```

Votre page est maintenant surveillée ! ArkWatch va :

1. Vérifier la page selon l'intervalle défini
2. Détecter les changements de contenu
3. Analyser les changements avec l'IA (résumé + importance)
4. Vous envoyer un email si un changement significatif est détecté

## Etape 4 : Consulter les rapports

Après le premier check, consultez vos rapports :

```bash
curl -X GET https://watch.arkforge.fr/api/v1/reports \
  -H "X-API-Key: ak_VOTRE_CLE"
```

Chaque rapport contient :

- **diff** : les changements détectés
- **ai_summary** : un résumé IA des modifications
- **ai_importance** : le niveau d'importance (high, medium, low)

## Etape 5 : Gérer vos watches

**Lister tous vos watches :**

```bash
curl -X GET https://watch.arkforge.fr/api/v1/watches \
  -H "X-API-Key: ak_VOTRE_CLE"
```

**Mettre un watch en pause :**

```bash
curl -X PATCH https://watch.arkforge.fr/api/v1/watches/WATCH_ID \
  -H "X-API-Key: ak_VOTRE_CLE" \
  -H "Content-Type: application/json" \
  -d '{"status": "paused"}'
```

**Supprimer un watch :**

```bash
curl -X DELETE https://watch.arkforge.fr/api/v1/watches/WATCH_ID \
  -H "X-API-Key: ak_VOTRE_CLE"
```

## Et ensuite ?

- Consultez les [Concepts](02-concepts.md) pour comprendre le fonctionnement en détail
- Parcourez l'[API Reference](03-api-reference.md) pour tous les endpoints
- Visitez la [FAQ](04-faq.md) si vous avez des questions
- Consultez le [Troubleshooting](05-troubleshooting.md) en cas de problème

## Offre gratuite

Le plan Free inclut :

| Fonctionnalité | Limite |
|---|---|
| Watches | 3 |
| Intervalle minimum | 24h |
| Alertes email | Incluses |
| Analyse IA | Incluse |
| Support RGPD | Complet |

Besoin de plus ? Consultez nos [plans payants](03-api-reference.md#plans-et-tarifs).
