# Conversion Tracking - ArkWatch

## Vue d'ensemble

Le système de tracking de conversion permet de suivre l'origine de chaque inscription (signup) et d'analyser l'efficacité de chaque canal d'acquisition.

## Architecture

### 1. Capture de la source (UTM tracking)

Chaque URL partagée doit inclure un paramètre `ref` pour identifier la source :

```
# Exemples d'URLs avec tracking
https://arkforge.fr/arkwatch.html?ref=devto
https://arkforge.fr/arkwatch.html?ref=ph          # ProductHunt
https://arkforge.fr/arkwatch.html?ref=outreach    # Email outreach
https://arkforge.fr/arkwatch.html?ref=twitter
https://arkforge.fr/arkwatch.html?ref=linkedin
```

### 2. Stockage dans la base de données

Lors de l'inscription (`POST /api/v1/auth/register`), le système :
1. Extrait le paramètre `ref` de l'URL
2. Stocke la valeur dans le champ `signup_source` de l'utilisateur
3. Par défaut, si aucun paramètre n'est fourni : `signup_source = "direct"`

**Structure de données** (dans `api_keys.json`) :
```json
{
  "user_hash_123": {
    "email": "user@example.com",
    "name": "John Doe",
    "tier": "free",
    "created_at": "2026-02-07T12:34:56",
    "signup_source": "devto",
    ...
  }
}
```

### 3. Endpoints d'analytics

#### GET `/api/stats`
**Accès** : Admin uniquement (requires `is_admin: true`)

Retourne les statistiques de conversion globales :
```json
{
  "total_signups": 145,
  "by_source": {
    "devto": 45,
    "ph": 23,
    "outreach": 12,
    "direct": 65
  },
  "by_day": {
    "2026-02-01": 12,
    "2026-02-02": 18,
    "2026-02-03": 15,
    ...
  },
  "by_source_and_day": {
    "2026-02-01": {
      "devto": 8,
      "direct": 4
    },
    "2026-02-02": {
      "ph": 10,
      "devto": 5,
      "direct": 3
    },
    ...
  }
}
```

#### GET `/api/stats/funnel`
**Accès** : Admin uniquement

Retourne les statistiques de funnel de conversion (signup → vérification email → paid) :
```json
{
  "total_signups": 145,
  "email_verified": 89,
  "paid_conversions": 12,
  "verification_rate": 61.38,
  "paid_conversion_rate": 8.28,
  "by_source": {
    "devto": {
      "signups": 45,
      "verified": 30,
      "paid": 8,
      "verification_rate": 66.67,
      "paid_rate": 17.78
    },
    "ph": {
      "signups": 23,
      "verified": 18,
      "paid": 2,
      "verification_rate": 78.26,
      "paid_rate": 8.7
    },
    ...
  }
}
```

## Guide d'utilisation

### Pour l'équipe Croissance

Lorsque vous partagez des liens vers ArkWatch, **TOUJOURS** ajouter le paramètre `?ref=` :

| Canal | Paramètre | URL complète |
|-------|-----------|--------------|
| Dev.to | `?ref=devto` | https://arkforge.fr/arkwatch.html?ref=devto |
| ProductHunt | `?ref=ph` | https://arkforge.fr/arkwatch.html?ref=ph |
| Email outreach | `?ref=outreach` | https://arkforge.fr/arkwatch.html?ref=outreach |
| Twitter | `?ref=twitter` | https://arkforge.fr/arkwatch.html?ref=twitter |
| LinkedIn | `?ref=linkedin` | https://arkforge.fr/arkwatch.html?ref=linkedin |
| Reddit | `?ref=reddit` | https://arkforge.fr/arkwatch.html?ref=reddit |
| Hacker News | `?ref=hn` | https://arkforge.fr/arkwatch.html?ref=hn |

**Conventions de nommage** :
- Minuscules uniquement
- Pas d'espaces (utilisez `-` si nécessaire : `email-campaign-1`)
- Court et descriptif (max 20 caractères recommandé)

### Pour consulter les stats

1. **Authentification** : Vous devez avoir un compte admin (flag `is_admin: true`)
2. **Requête API** :
```bash
curl -X GET "https://watch.arkforge.fr/api/stats" \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

3. **Via le dashboard** (à venir) : Interface web dédiée pour visualiser les métriques

## Migration des données existantes

Les utilisateurs créés **avant** cette implémentation auront automatiquement `signup_source: "direct"` car le champ n'existait pas.

Pour rétroactivement identifier certaines sources (si vous avez des informations externes), vous pouvez modifier manuellement `api_keys.json` :
```bash
# Backup first!
cp data/api_keys.json data/api_keys.json.backup

# Edit manually (careful with JSON encryption!)
# Les champs PII sont chiffrés, ne modifiez que signup_source
```

## Monitoring et alertes

**Recommandations** :
1. Consulter `/api/stats` quotidiennement pour suivre les tendances
2. Comparer les taux de conversion par source (funnel endpoint)
3. Identifier les sources à fort taux de conversion → doubler les efforts
4. Identifier les sources à faible taux → analyser et optimiser ou abandonner

**Métriques clés** :
- **Taux de vérification email** : cible > 60%
- **Taux de conversion paid** : cible > 5%
- **Coût par acquisition** : à calculer manuellement (temps investi / signups)

## Exemples de requêtes

### Bash / curl
```bash
# Stats globales
curl -X GET "https://watch.arkforge.fr/api/stats" \
  -H "X-API-Key: ak_YOUR_ADMIN_KEY"

# Funnel par source
curl -X GET "https://watch.arkforge.fr/api/stats/funnel" \
  -H "X-API-Key: ak_YOUR_ADMIN_KEY"
```

### Python
```python
import requests

API_KEY = "ak_YOUR_ADMIN_KEY"
BASE_URL = "https://watch.arkforge.fr"

headers = {"X-API-Key": API_KEY}

# Get conversion stats
stats = requests.get(f"{BASE_URL}/api/stats", headers=headers).json()
print(f"Total signups: {stats['total_signups']}")
print(f"By source: {stats['by_source']}")

# Get funnel stats
funnel = requests.get(f"{BASE_URL}/api/stats/funnel", headers=headers).json()
print(f"Verification rate: {funnel['verification_rate']}%")
print(f"Paid conversion rate: {funnel['paid_conversion_rate']}%")
```

### JavaScript (frontend)
```javascript
const API_KEY = 'ak_YOUR_ADMIN_KEY';
const BASE_URL = 'https://watch.arkforge.fr';

async function getStats() {
  const response = await fetch(`${BASE_URL}/api/stats`, {
    headers: { 'X-API-Key': API_KEY }
  });
  const data = await response.json();
  console.log('Total signups:', data.total_signups);
  console.log('By source:', data.by_source);
}

getStats();
```

## Sécurité et RGPD

- ✅ Le tracking est **interne uniquement** (pas de Google Analytics, pas de third-party)
- ✅ Les données sont stockées dans `api_keys.json` (chiffrement des PII existant)
- ✅ Le champ `signup_source` n'est **PAS considéré comme PII** (non chiffré)
- ✅ Accès admin uniquement pour consulter les stats (protection par `is_admin` flag)
- ✅ Conforme RGPD : données minimales, pas de cookies tiers, pas de tracking cross-site

## Maintenance

**Fichiers modifiés** :
- `/src/api/auth.py` : ajout paramètre `signup_source` dans `create_api_key()`
- `/src/api/routers/auth.py` : capture du paramètre `?ref=` dans `/register`
- `/src/api/routers/stats.py` : nouveaux endpoints `/api/stats` et `/api/stats/funnel`
- `/src/api/main.py` : enregistrement du router `stats`

**Tests recommandés** :
- [ ] Signup sans `?ref=` → vérifie `signup_source = "direct"`
- [ ] Signup avec `?ref=devto` → vérifie `signup_source = "devto"`
- [ ] GET `/api/stats` sans admin → HTTP 403
- [ ] GET `/api/stats` avec admin → retourne données valides
- [ ] GET `/api/stats/funnel` → calcul correct des taux

## Roadmap

**V1 (actuel)** :
- ✅ Capture source via `?ref=`
- ✅ Stockage dans DB
- ✅ Endpoints stats admin

**V2 (futur)** :
- [ ] Dashboard web pour visualiser les stats (charts)
- [ ] Export CSV des données
- [ ] Alertes automatiques (ex: "source X a converti 0 signups cette semaine")
- [ ] A/B testing de landing pages par source
- [ ] Attribution multi-touch (premier clic + dernier clic)

---

**Contact** : Pour toute question, contactez le worker Fondations ou le CEO.
