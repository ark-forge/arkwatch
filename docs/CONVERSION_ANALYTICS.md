# ArkWatch - Conversion Analytics & UTM Tracking

## Vue d'ensemble

Le système de tracking de conversion permet de mesurer l'efficacité de chaque canal marketing en suivant la source de chaque signup. Les données sont ensuite accessibles via l'API analytics.

## Architecture

### 1. Capture de la source (Frontend)

Lors de l'inscription, le paramètre `?ref=` est capturé automatiquement :

```
https://arkforge.fr/arkwatch.html?ref=devto
https://arkforge.fr/arkwatch.html?ref=producthunt
https://arkforge.fr/arkwatch.html?ref=outreach
https://arkforge.fr/arkwatch.html?ref=twitter
```

### 2. Enregistrement (Backend)

Le endpoint `/api/v1/auth/register` capture automatiquement le paramètre `ref` et le stocke dans le champ `signup_source` de l'utilisateur.

**Code (déjà implémenté)** :
```python
# auth.py, ligne 277
signup_source = request.query_params.get("ref", "direct")

# auth.py, ligne 280-287
raw_key, _, verification_code = create_api_key(
    name=name,
    email=req.email,
    tier="free",
    privacy_accepted=True,
    client_ip=client_ip,
    signup_source=signup_source,  # ← stocké ici
)
```

### 3. Analytics (Endpoints)

Deux endpoints pour consulter les données :

#### `/api/stats` (admin-only)
Retourne les signups par source et par jour :

```json
{
  "total_signups": 42,
  "by_source": {
    "direct": 15,
    "devto": 12,
    "producthunt": 8,
    "twitter": 7
  },
  "by_day": {
    "2026-02-06": 18,
    "2026-02-07": 24
  },
  "by_source_and_day": {
    "2026-02-06": {
      "direct": 6,
      "devto": 7,
      "twitter": 5
    },
    "2026-02-07": {
      "direct": 9,
      "devto": 5,
      "producthunt": 8,
      "twitter": 2
    }
  }
}
```

#### `/api/stats/funnel` (admin-only)
Retourne les métriques de conversion (signup → verified → paid) :

```json
{
  "total_signups": 42,
  "email_verified": 28,
  "paid_conversions": 3,
  "verification_rate": 66.67,
  "paid_conversion_rate": 7.14,
  "by_source": {
    "direct": {
      "signups": 15,
      "verified": 12,
      "paid": 2,
      "verification_rate": 80.0,
      "paid_rate": 13.33
    },
    "devto": {
      "signups": 12,
      "verified": 8,
      "paid": 1,
      "verification_rate": 66.67,
      "paid_rate": 8.33
    }
  }
}
```

## Nomenclature des sources recommandée

### Canaux externes

| Canal | Paramètre | URL complète |
|-------|-----------|--------------|
| Dev.to | `?ref=devto` | `https://arkforge.fr/arkwatch.html?ref=devto` |
| Product Hunt | `?ref=producthunt` | `https://arkforge.fr/arkwatch.html?ref=producthunt` |
| Hacker News | `?ref=hackernews` | `https://arkforge.fr/arkwatch.html?ref=hackernews` |
| Reddit | `?ref=reddit` | `https://arkforge.fr/arkwatch.html?ref=reddit` |
| Twitter | `?ref=twitter` | `https://arkforge.fr/arkwatch.html?ref=twitter` |
| LinkedIn | `?ref=linkedin` | `https://arkforge.fr/arkwatch.html?ref=linkedin` |

### Campagnes spécifiques

Pour des campagnes ciblées, utilisez des identifiants plus précis :

| Campagne | Paramètre | Exemple |
|----------|-----------|---------|
| Email outreach | `?ref=outreach_jan2026` | Campagne email de janvier |
| Guest post | `?ref=guestpost_blog1` | Article invité sur blog1 |
| Partnership | `?ref=partner_acme` | Partenariat avec Acme Inc |
| Ad campaign | `?ref=ads_google_search` | Google Ads - Search |

### Trafic organique

Si aucun paramètre `ref` n'est fourni, la source est enregistrée comme `"direct"`.

## Guide d'utilisation

### 1. Ajouter le paramètre aux liens partagés

**Sur Dev.to** :
```
Découvrez ArkWatch, un outil de monitoring web avec résumés IA :
👉 https://arkforge.fr/arkwatch.html?ref=devto
```

**Sur Product Hunt** :
```
Landing page: https://arkforge.fr/arkwatch.html?ref=producthunt
```

**Email outreach** :
```html
<a href="https://arkforge.fr/arkwatch.html?ref=outreach_feb2026">
  Découvrir ArkWatch
</a>
```

### 2. Consulter les analytics

**Prérequis** : Compte admin requis

```bash
# Via curl
curl -H "X-API-Key: YOUR_ADMIN_KEY" https://watch.arkforge.fr/api/stats

# Via Python
import requests
headers = {"X-API-Key": "YOUR_ADMIN_KEY"}
response = requests.get("https://watch.arkforge.fr/api/stats", headers=headers)
print(response.json())
```

### 3. Analyser les données

#### Identifier les canaux performants
```python
stats = response.json()
best_source = max(stats["by_source"].items(), key=lambda x: x[1])
print(f"Meilleur canal: {best_source[0]} avec {best_source[1]} signups")
```

#### Suivre la tendance quotidienne
```python
funnel = requests.get("https://watch.arkforge.fr/api/stats/funnel", headers=headers).json()
for source, metrics in funnel["by_source"].items():
    print(f"{source}: {metrics['verification_rate']}% vérifiés, {metrics['paid_rate']}% payants")
```

## Limitations actuelles

1. **Pas de multi-attribution** : Seul le paramètre `ref` lors du signup est enregistré. Si un utilisateur visite le site via plusieurs canaux, seul le dernier avant le signup est tracké.

2. **Pas de tracking de navigation** : On ne suit pas les pages visitées avant le signup, seulement la source d'entrée.

3. **Pas de third-party analytics** : Pas de Google Analytics, Mixpanel, etc. Uniquement des logs internes pour respecter le RGPD et garder le contrôle des données.

## Roadmap

- [ ] Ajouter un tableau de bord visuel (graphiques) pour les analytics
- [ ] Exporter les stats en CSV pour analyse externe
- [ ] Tracking de l'attribution multi-touch (premier + dernier canal)
- [ ] Webhooks pour alertes sur pics de signups
- [ ] Intégration avec outils CRM (optionnel)

## Sécurité et RGPD

✅ **Conforme RGPD** :
- Les données de source sont anonymes (pas de tracking cross-site)
- Uniquement stockées pour les utilisateurs qui ont accepté la privacy policy
- Accessibles uniquement par les admins
- Supprimées avec le compte utilisateur (GDPR Art. 17)

✅ **Pas de cookies tiers** :
- Pas de scripts de tracking externe
- Pas de partage de données avec des services tiers
- Contrôle total des données
