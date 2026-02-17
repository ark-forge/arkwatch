# Quick Start - Analytics de conversion ArkWatch

## 🚀 Démarrage rapide (pour le CEO)

Ce guide vous permet de commencer à utiliser les analytics de conversion en 5 minutes.

---

## 1️⃣ Créer des liens trackés

### Pour partager sur Twitter
```
https://arkforge.fr/arkwatch.html?ref=twitter
```

### Pour partager sur Dev.to
```
https://arkforge.fr/arkwatch.html?ref=devto
```

### Pour un email de prospection
```
https://arkforge.fr/arkwatch.html?ref=outreach
```

**Règle simple** : Ajoutez `?ref=NOM_DU_CANAL` à vos liens.

---

## 2️⃣ Consulter les stats (admin-only)

### Prérequis
Vous devez avoir une clé API admin. Si vous n'en avez pas :

```bash
cd /opt/claude-ceo/workspace/arkwatch
source venv/bin/activate
python3 src/api/auth.py create admin@arkforge.fr admin
```

### Commandes

#### Voir les signups par source
```bash
curl -H "X-API-Key: VOTRE_CLE_ADMIN" https://watch.arkforge.fr/api/stats
```

**Exemple de réponse** :
```json
{
  "total_signups": 42,
  "by_source": {
    "twitter": 15,
    "devto": 12,
    "direct": 10,
    "producthunt": 5
  },
  "by_day": {
    "2026-02-06": 18,
    "2026-02-07": 24
  }
}
```

#### Voir le funnel de conversion
```bash
curl -H "X-API-Key: VOTRE_CLE_ADMIN" https://watch.arkforge.fr/api/stats/funnel
```

**Exemple de réponse** :
```json
{
  "total_signups": 42,
  "email_verified": 28,
  "paid_conversions": 3,
  "verification_rate": 66.67,
  "paid_conversion_rate": 7.14,
  "by_source": {
    "twitter": {
      "signups": 15,
      "verified": 12,
      "paid": 2,
      "verification_rate": 80.0,
      "paid_rate": 13.33
    }
  }
}
```

---

## 3️⃣ Analyser les données

### Identifier le meilleur canal

```bash
# Récupérer les stats
curl -s -H "X-API-Key: VOTRE_CLE_ADMIN" https://watch.arkforge.fr/api/stats | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  sources = data['by_source']; \
  best = max(sources.items(), key=lambda x: x[1]); \
  print(f'Meilleur canal: {best[0]} avec {best[1]} signups')"
```

### Comparer les taux de conversion

```bash
# Récupérer le funnel
curl -s -H "X-API-Key: VOTRE_CLE_ADMIN" https://watch.arkforge.fr/api/stats/funnel | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  for source, metrics in data['by_source'].items(): \
    print(f'{source:15} | Signups: {metrics[\"signups\"]:3} | Verified: {metrics[\"verification_rate\"]:5.1f}% | Paid: {metrics[\"paid_rate\"]:5.1f}%')"
```

---

## 4️⃣ Exemples de décisions data-driven

### Scénario 1: Twitter convertit mieux que Dev.to

**Données** :
- Twitter: 15 signups, 80% vérifiés, 13% payants
- Dev.to: 20 signups, 40% vérifiés, 2% payants

**Décision** :
→ Investir plus de temps sur Twitter, améliorer la stratégie Dev.to

### Scénario 2: Taux de vérification faible

**Données** :
- 100 signups, 30% vérifiés seulement

**Décision** :
→ Améliorer le processus d'onboarding (email de bienvenue, rappels)

### Scénario 3: Un canal inattendu performe bien

**Données** :
- Reddit: 5 signups, 100% vérifiés, 40% payants

**Décision** :
→ Investir davantage sur Reddit (petite audience mais très qualifiée)

---

## 5️⃣ Automatiser le reporting

### Script quotidien pour recevoir les stats par email

```bash
#!/bin/bash
# daily_stats.sh - À mettre dans un cron

ADMIN_KEY="votre_cle_admin"
STATS=$(curl -s -H "X-API-Key: $ADMIN_KEY" https://watch.arkforge.fr/api/stats)

# Parser et formater
TOTAL=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_signups'])")
BY_SOURCE=$(echo "$STATS" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)['by_source'], indent=2))")

# Envoyer par email
echo "Signups total: $TOTAL

Par source:
$BY_SOURCE" | mail -s "ArkWatch Daily Stats" apps.desiorac@gmail.com
```

### Ajouter au cron (tous les jours à 9h)
```bash
crontab -e
# Ajouter:
0 9 * * * /opt/claude-ceo/scripts/daily_stats.sh
```

---

## 6️⃣ Dashboard visuel (optionnel)

Pour une visualisation graphique, créer un dashboard HTML simple :

```html
<!DOCTYPE html>
<html>
<head>
  <title>ArkWatch Analytics</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>ArkWatch - Analytics</h1>
  <canvas id="chart"></canvas>

  <script>
    const API_KEY = 'VOTRE_CLE_ADMIN';

    fetch('https://watch.arkforge.fr/api/stats', {
      headers: {'X-API-Key': API_KEY}
    })
    .then(r => r.json())
    .then(data => {
      new Chart(document.getElementById('chart'), {
        type: 'bar',
        data: {
          labels: Object.keys(data.by_source),
          datasets: [{
            label: 'Signups par source',
            data: Object.values(data.by_source)
          }]
        }
      });
    });
  </script>
</body>
</html>
```

---

## 📚 Documentation complète

- **Technique** : `/opt/claude-ceo/workspace/arkwatch/docs/CONVERSION_ANALYTICS.md`
- **Marketing** : `/opt/claude-ceo/workspace/arkwatch/docs/UTM_GUIDE_MARKETING.md`

---

## ✅ Checklist de démarrage

- [ ] Créer une clé API admin si pas déjà fait
- [ ] Tester `/api/stats` pour voir les données actuelles
- [ ] Partager un premier lien tracké (ex: `?ref=twitter`)
- [ ] Vérifier après 24h que le signup est compté dans les stats
- [ ] Configurer un reporting automatique (optionnel)

---

## 🆘 Support

**Problème d'accès aux stats ?**
→ Vérifier que votre clé API a le flag `is_admin: true`

**Pas de données dans les stats ?**
→ Vérifier que les liens partagés contiennent bien `?ref=`

**Questions techniques ?**
→ Consulter `docs/CONVERSION_ANALYTICS.md`

---

**Version** : 1.0
**Date** : 2026-02-07
**Auteur** : Worker Fondations
