# ArkWatch - Concepts

Ce guide explique les concepts fondamentaux d'ArkWatch.

## Vue d'ensemble

ArkWatch est un service de surveillance de pages web alimenté par l'IA. Il détecte les changements sur les pages que vous suivez, génère des résumés intelligents, et vous alerte par email.

```
Vous créez un Watch
        ↓
ArkWatch vérifie la page périodiquement
        ↓
Changement détecté ?
    ├─ Non → Prochain check selon l'intervalle
    └─ Oui → Analyse IA + Rapport + Alerte email
```

## Watch (Surveillance)

Un **Watch** est l'objet central d'ArkWatch. Il représente la surveillance d'une page web spécifique.

### Propriétés d'un Watch

| Propriété | Description |
|---|---|
| `id` | Identifiant unique (UUID) |
| `url` | L'URL de la page surveillée |
| `name` | Nom donné au watch pour l'identifier |
| `check_interval` | Fréquence de vérification en secondes |
| `notify_email` | Email pour recevoir les alertes |
| `min_change_ratio` | Seuil minimum de changement pour déclencher une alerte (0.0 à 1.0) |
| `status` | Etat actuel : `active`, `paused`, ou `error` |

### Cycle de vie d'un Watch

```
Création (active)
    ↓
┌─ Vérification périodique ←─┐
│   ↓                        │
│ Changement ?               │
│   ├─ Non ──────────────────┘
│   └─ Oui → Rapport + Alerte
│               ↓
│         Prochain check ─────┘
│
├─ Pause (paused) → Reprise (active)
│
└─ Suppression
```

### Statuts

- **active** : le watch est opérationnel, les vérifications ont lieu selon l'intervalle défini
- **paused** : le watch est en pause, aucune vérification n'est effectuée
- **error** : une erreur s'est produite lors d'une vérification (URL inaccessible, timeout, etc.)

### Intervalle de vérification

L'intervalle (`check_interval`) détermine la fréquence à laquelle ArkWatch vérifie la page. Il est exprimé en secondes :

| Valeur | Fréquence |
|---|---|
| 60 | Toutes les minutes |
| 300 | Toutes les 5 minutes |
| 3600 | Toutes les heures |
| 86400 | Toutes les 24 heures |

L'intervalle minimum dépend de votre plan (voir [Plans et tarifs](#plans-et-tarifs)).

### Seuil de changement

Le `min_change_ratio` contrôle la sensibilité de la détection :

- **0.01** (1%) : très sensible, alerte au moindre changement
- **0.05** (5%) : sensibilité par défaut, ignore les changements mineurs
- **0.20** (20%) : peu sensible, ne signale que les changements importants

## Alert (Alerte)

Une **Alerte** est une notification email envoyée lorsqu'un changement significatif est détecté.

### Contenu d'une alerte

Chaque alerte email contient :

- Le nom du watch concerné
- L'URL surveillée
- Un résumé IA des changements
- Le niveau d'importance estimé par l'IA
- Un lien vers le rapport complet

### Désinscription

Chaque email contient un lien de désinscription conforme au RGPD. Cliquer sur ce lien désactive les notifications pour tous vos watches, sans supprimer votre compte ni vos watches.

## Report (Rapport)

Un **Rapport** est généré à chaque fois qu'un changement est détecté sur un watch.

### Propriétés d'un Rapport

| Propriété | Description |
|---|---|
| `id` | Identifiant unique (UUID) |
| `watch_id` | Le watch associé |
| `changes_detected` | `true` si des changements ont été détectés |
| `diff` | Les différences textuelles entre l'ancienne et la nouvelle version |
| `ai_summary` | Résumé IA des changements en langage naturel |
| `ai_importance` | Niveau d'importance : `high`, `medium`, `low` |
| `notified` | `true` si une alerte email a été envoyée |
| `created_at` | Date et heure du rapport |

### Niveaux d'importance IA

L'IA analyse les changements et leur attribue un niveau d'importance :

- **high** : changement majeur (nouvelle fonctionnalité, modification de prix, annonce importante)
- **medium** : changement notable (mise à jour de contenu, correction)
- **low** : changement mineur (typo, reformulation, mise à jour de date)

## Authentification

### Clé API

L'authentification utilise des clés API au format `ak_<token>`. La clé est transmise via le header HTTP :

```
X-API-Key: ak_votre_cle_ici
```

### Vérification email

Après l'inscription, un code à 6 chiffres est envoyé par email. La vérification est requise pour :

- Créer des watches
- Modifier votre compte
- Accéder aux fonctionnalités principales

Les opérations RGPD (export de données, suppression de compte) restent accessibles sans vérification.

## Plans et tarifs

| Plan | Watches | Intervalle min | Prix |
|---|---|---|---|
| **Free** | 3 | 24 heures | Gratuit |
| **Starter** | 10 | 1 heure | Voir site |
| **Pro** | 50 | 5 minutes | Voir site |
| **Business** | 1000 | 1 minute | Voir site |

### Changement de plan

- **Upgrade** : immédiat, les nouvelles limites s'appliquent aussitôt
- **Downgrade** : effectif à la fin de la période de facturation en cours
- Si vous dépassez les limites de votre nouveau plan après un downgrade, vos watches existants restent actifs mais vous ne pouvez pas en créer de nouveaux

## RGPD et vie privée

ArkWatch est conforme au RGPD. Vos droits :

| Droit | Comment l'exercer |
|---|---|
| **Accès** (Art. 15) | `GET /api/v1/auth/account/data` |
| **Rectification** (Art. 16) | `PATCH /api/v1/auth/account` |
| **Effacement** (Art. 17) | `DELETE /api/v1/auth/account` |
| **Opposition** (Art. 21) | Lien de désinscription dans les emails |

### Protection des données

- Les emails et noms sont chiffrés au repos (Fernet AES-128-CBC)
- Les clés API sont hashées (SHA-256)
- Protection SSRF sur les URLs surveillées
- CORS restreint au domaine arkforge.fr
