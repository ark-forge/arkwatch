# ArkWatch - FAQ

## Général

### Qu'est-ce qu'ArkWatch ?

ArkWatch est un service de surveillance de pages web alimenté par l'IA. Il vérifie automatiquement les pages que vous suivez, détecte les changements, et vous envoie des alertes avec un résumé intelligent.

### Quels types de pages puis-je surveiller ?

Vous pouvez surveiller toute page web accessible publiquement via HTTPS. Exemples courants :

- Pages de prix de produits
- Pages de statut de services
- Offres d'emploi
- Pages de documentation
- Blogs et actualités
- Pages de concurrents

### L'API est-elle gratuite ?

Oui, le plan Free est gratuit et inclut 3 watches avec un intervalle de vérification de 24 heures. Aucune carte de crédit n'est requise pour s'inscrire.

### Quel est le format de la clé API ?

Les clés API ont le format `ak_<token>`. Elles sont générées lors de l'inscription et doivent être transmises via le header `X-API-Key`.

---

## Watches

### Combien de watches puis-je créer ?

Cela dépend de votre plan :

| Plan | Watches max |
|---|---|
| Free | 3 |
| Starter | 10 |
| Pro | 50 |
| Business | 1000 |

### Quel intervalle de vérification choisir ?

- **24h** (86400s) : idéal pour les pages qui changent rarement (blogs, documentation)
- **1h** (3600s) : bon pour les pages de prix, offres d'emploi
- **5min** (300s) : pour les pages critiques qui nécessitent une réactivité rapide
- **1min** (60s) : pour le monitoring en temps quasi-réel (plan Business)

### Qu'est-ce que le seuil de changement (min_change_ratio) ?

C'est un pourcentage entre 0.0 et 1.0 qui détermine la sensibilité de la détection. Par exemple, `0.05` signifie que la page doit changer d'au moins 5% pour déclencher une alerte. Cela évite les fausses alertes dues à des changements mineurs (date, compteur de visites, etc.).

### Puis-je surveiller des pages qui nécessitent une connexion ?

Non, ArkWatch ne supporte pas l'authentification sur les pages surveillées. Seules les pages accessibles publiquement peuvent être surveillées.

### Que se passe-t-il si une page surveillée est temporairement indisponible ?

Le watch passe en statut `error`. ArkWatch continuera les vérifications selon l'intervalle défini. Si la page redevient accessible, le watch repasse automatiquement en `active`.

---

## Alertes et Rapports

### Comment sont envoyées les alertes ?

Les alertes sont envoyées par email à l'adresse configurée dans le watch (par défaut, l'email du compte).

### Que contient un rapport ?

Chaque rapport inclut :

- **diff** : les changements textuels détectés entre deux vérifications
- **ai_summary** : un résumé en langage naturel généré par l'IA
- **ai_importance** : un niveau d'importance (high, medium, low)
- **created_at** : la date du rapport

### Comment fonctionne l'analyse IA ?

ArkWatch utilise l'IA Mistral pour analyser les changements détectés. L'IA génère un résumé compréhensible et évalue l'importance du changement pour vous aider à prioriser.

### Je ne reçois pas les emails d'alerte

Vérifiez les points suivants :

1. Votre email est vérifié (vérifiez via l'inscription)
2. Vous ne vous êtes pas désinscrit (check le lien de désinscription)
3. Vérifiez votre dossier spam
4. Le watch est en statut `active`
5. Le changement dépasse le seuil `min_change_ratio`

---

## Compte et facturation

### Comment changer de plan ?

Utilisez l'endpoint `POST /api/v1/billing/checkout` avec le tier souhaité. Vous serez redirigé vers Stripe pour le paiement.

### Comment annuler mon abonnement ?

Utilisez `POST /api/v1/billing/cancel`. L'annulation prend effet à la fin de la période de facturation en cours. Vous repassez ensuite au plan Free.

### Que se passe-t-il si j'ai plus de watches que la limite du plan Free après un downgrade ?

Vos watches existants restent actifs, mais vous ne pourrez pas en créer de nouveaux tant que vous n'êtes pas repassé sous la limite.

### Comment supprimer mon compte ?

Utilisez `DELETE /api/v1/auth/account`. Cette action supprime irréversiblement votre compte, tous vos watches, rapports, et annule tout abonnement actif.

---

## RGPD et vie privée

### Quelles données ArkWatch collecte-t-il ?

- Email (chiffré au repos)
- Nom (chiffré au repos)
- URLs des pages surveillées
- Contenus des pages et rapports d'analyse

### Comment exercer mes droits RGPD ?

| Droit | Endpoint |
|---|---|
| Accès aux données | `GET /api/v1/auth/account/data` |
| Rectification | `PATCH /api/v1/auth/account` |
| Suppression | `DELETE /api/v1/auth/account` |
| Opposition (emails) | Lien dans chaque email ou `GET /api/v1/auth/unsubscribe` |

### Mes données sont-elles en sécurité ?

Oui. ArkWatch implémente :

- Chiffrement des données personnelles au repos (Fernet AES-128-CBC)
- Hashage des clés API (SHA-256)
- Protection SSRF sur les URLs
- CORS restreint
- Vérification de signature Stripe pour les webhooks

### Où sont hébergées les données ?

Les données sont hébergées en Europe, conformément au RGPD.

---

## Sécurité

### Pourquoi certaines URLs sont-elles refusées ?

ArkWatch bloque les URLs pointant vers des adresses IP privées (localhost, 10.x.x.x, 192.168.x.x, etc.) pour prévenir les attaques SSRF. Seules les URLs publiques HTTPS sont acceptées.

### Ma clé API a-t-elle été compromise, que faire ?

Supprimez votre compte (`DELETE /api/v1/auth/account`) et créez-en un nouveau. Il n'existe pas actuellement de mécanisme de rotation de clé API.
