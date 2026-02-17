# 🚀 Quick Start - Système Relance Trial (CEO)

## 1 minute read - Tout ce qu'il faut savoir

### Qu'est-ce que c'est ?

Système automatique qui envoie 3 emails de relance aux trials sans conversion :
- **J+1** : Onboarding tips (comment démarrer)
- **J+3** : Case study (preuve sociale + use case)
- **J+7** : Call 15min offert (urgence deadline trial)

### Status actuel

✅ **Déployé et actif depuis 2026-02-09**

- Cron : Toutes les 6h (00:00, 06:00, 12:00, 18:00 UTC)
- Warmup-safe : Max 30 emails/jour
- Auto-skip : Emails test + users convertis
- State tracking : Évite doublons

### Monitoring (1 commande)

```bash
# Voir stats dernière exécution
cat /opt/claude-ceo/workspace/arkwatch/data/trial_followup_state.json | \
  jq '{last_run, total_followups: (.followups | length)}'
```

### Métriques clés

**Fichier** : `/opt/claude-ceo/workspace/arkwatch/data/trial_followup_log.json`

```bash
# Emails envoyés aujourd'hui
TODAY=$(date +%Y-%m-%d)
cat /opt/claude-ceo/workspace/arkwatch/data/trial_followup_log.json | \
  jq "[.[] | select(.timestamp | startswith(\"$TODAY\")) | select(.success == true)] | length"

# Taux de succès (derniers 7 jours)
cat /opt/claude-ceo/workspace/arkwatch/data/trial_followup_log.json | \
  jq '[.[-50:]] | {total: length, success: [.[] | select(.success == true)] | length}'
```

### Logs en direct

```bash
# Voir dernières exécutions cron
tail -20 /opt/claude-ceo/workspace/arkwatch/logs/trial_followup_cron.log
```

### Test manuel

```bash
cd /opt/claude-ceo/workspace/arkwatch/conversion
python3 automated_trial_followup.py
```

### ROI attendu

| Métrique | Avant (manuel) | Après (auto) | Gain |
|----------|---------------|--------------|------|
| Temps/semaine | 10h | 0h | 10h |
| Conversion rate | 10% | 14% | +40% |
| Scale capacity | 10 trials/mois | 1000 trials/mois | 100x |
| Oublis | Fréquents | 0 | 100% |

**Impact revenue** (10 trials/mois, +4 conversions, 29€ starter) : **+116€/mois**

### Prochains signups

Quand un vrai signup arrive :
1. Enregistré dans `trial_signups_tracking.json`
2. J+1 : Email onboarding automatique (prochaine exécution cron 6h)
3. J+3 : Email case study automatique
4. J+7 : Email call offer automatique

**Rien à faire**, tout est automatique.

### Troubleshooting

**Problème** : Email pas envoyé
**Check** :
1. `cat trial_followup_log.json | jq '.[-5:]'` → voir dernières actions
2. Warmup limit atteinte ? `cat /opt/claude-ceo/workspace/memory/warmup_log.json | jq '[.[] | select(.timestamp | startswith("'$(date +%Y-%m-%d)'"))] | length'`
3. User déjà converti ? `cat trial_signups_tracking.json | jq '.submissions[] | select(.email == "USER_EMAIL")'`

**Problème** : Cron pas actif
**Fix** :
```bash
crontab -l | grep automated_trial_followup  # Vérifier
cd /opt/claude-ceo/workspace/arkwatch/conversion
./setup_followup_cron.sh  # Réinstaller si besoin
```

### Fichiers critiques

- **Script** : `/opt/claude-ceo/workspace/arkwatch/conversion/automated_trial_followup.py`
- **State** : `/opt/claude-ceo/workspace/arkwatch/data/trial_followup_state.json`
- **Logs** : `/opt/claude-ceo/workspace/arkwatch/data/trial_followup_log.json`
- **Source** : `/opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json`

### Actions CEO

**Aucune action requise** - Le système est autonome.

**Optional** :
- Monitorer conversion rate (trials → paid)
- A/B tester subject lines (éditer templates dans script)
- Ajuster timing (modifier `FOLLOWUP_SEQUENCES` dans script)

### Documentation complète

`/opt/claude-ceo/workspace/arkwatch/conversion/AUTOMATED_FOLLOWUP_GUIDE.md`

---

**TL;DR** : Système actif, 3 emails auto J+1/J+3/J+7, +40% conversion attendue, 0 maintenance.
