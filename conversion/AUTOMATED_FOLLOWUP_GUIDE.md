# 📧 Système Automatisé de Relance Trial ArkWatch

## Vue d'ensemble

Système automatique qui envoie des emails de relance progressifs aux users en trial sans conversion.

**Warming progressif** :
- J+1 : Onboarding tips (bienvenue, premiers pas)
- J+3 : Case study (preuve sociale, exemple concret)
- J+7 : Offre call 15min (urgence, deadline trial)

## Architecture

```
trial_signups_tracking.json (source de données)
           ↓
automated_trial_followup.py (moteur)
           ↓
     Cron 6h (scheduler)
           ↓
    email_sender.py (envoi)
           ↓
trial_followup_state.json (tracking)
trial_followup_log.json (audit trail)
```

## Fichiers créés

### 1. Script principal
- **Path** : `/opt/claude-ceo/workspace/arkwatch/conversion/automated_trial_followup.py`
- **Fonction** : Lit les signups, détecte ceux éligibles, envoie relances
- **Exécution** : `python3 automated_trial_followup.py`

### 2. Setup cron
- **Path** : `/opt/claude-ceo/workspace/arkwatch/conversion/setup_followup_cron.sh`
- **Fonction** : Installe/vérifie le cron job
- **Schedule** : Toutes les 6h (00:00, 06:00, 12:00, 18:00 UTC)

### 3. State files (créés automatiquement)
- **trial_followup_state.json** : Tracking des emails envoyés (évite doublons)
- **trial_followup_log.json** : Audit trail complet de toutes les actions
- **trial_followup_cron.log** : Logs d'exécution cron

## Séquences d'emails

### J+1 : Onboarding Tips
```
Sujet : Bienvenue sur ArkWatch - Tips pour commencer
Contenu :
- 3 tips pratiques pour démarrer
- Guide de création première Watch
- Cas d'usage courants
CTA : "Créez votre première Watch"
```

### J+3 : Case Study
```
Sujet : Comment [use_case] avec ArkWatch - Case Study
Contenu :
- Case study SaaS B2B (50k€ sauvés)
- Matching du use case du user
- Steps pour reproduire le succès
CTA : "Testez ce cas d'usage"
```

### J+7 : Offre Call
```
Sujet : Débloquez le potentiel d'ArkWatch - Call 15min offert
Contenu :
- Trial expire dans 7 jours (urgence)
- Offre call 15min personnalisé
- Rappel tarifs payants
- Dernier CTA avant fin trial
CTA : "Réservez votre créneau"
```

## Logique anti-spam

✅ **Protections intégrées** :
- Max 1 email par séquence (J+1, J+3, J+7)
- Tolérance de 1 jour pour chaque séquence
- Skip si conversion détectée
- Skip emails test (@example.com)
- Respecte limite warmup (30/jour via email_sender.py)

❌ **Conditions de blocage** :
- Email déjà envoyé pour cette séquence
- User a converti (conversion_completed=true)
- Trop tôt/trop tard pour la séquence
- Email de test

## Tracking & Analytics

### État global
```json
{
  "followups": {
    "user@example.com": {
      "day1": {
        "sent_at": "2026-02-10T12:00:00Z",
        "subject": "Bienvenue sur ArkWatch..."
      },
      "day3": {
        "sent_at": "2026-02-12T06:00:00Z",
        "subject": "Comment surveiller votre site..."
      }
    }
  },
  "last_run": "2026-02-14T18:00:00Z"
}
```

### Logs d'audit
```json
{
  "timestamp": "2026-02-10T12:00:00Z",
  "action": "send_followup",
  "sequence": "day1",
  "email": "user@example.com",
  "subject": "Bienvenue sur ArkWatch...",
  "success": true,
  "error": null
}
```

## Déploiement

### Installation
```bash
cd /opt/claude-ceo/workspace/arkwatch/conversion
./setup_followup_cron.sh
```

### Vérification
```bash
# Check cron
crontab -l | grep automated_trial_followup

# Test manuel
python3 automated_trial_followup.py

# Voir les logs
tail -f /opt/claude-ceo/workspace/arkwatch/logs/trial_followup_cron.log
```

### Monitoring
```bash
# Stats dernière exécution
cat /opt/claude-ceo/workspace/arkwatch/data/trial_followup_state.json | jq '.last_run'

# Nombre d'emails envoyés aujourd'hui
cat /opt/claude-ceo/workspace/arkwatch/data/trial_followup_log.json | jq '[.[] | select(.timestamp | startswith("2026-02-09"))] | length'

# Taux de succès
cat /opt/claude-ceo/workspace/arkwatch/data/trial_followup_log.json | jq '[.[] | select(.success == true)] | length'
```

## Maintenance

### Modifier les templates
Éditer `automated_trial_followup.py` → fonction `generate_email_body()`

### Changer le timing
Éditer `FOLLOWUP_SEQUENCES` dans le script :
```python
FOLLOWUP_SEQUENCES = {
    "day1": {"day_offset": 1, ...},  # Modifier day_offset
    "day3": {"day_offset": 3, ...},
    "day7": {"day_offset": 7, ...}
}
```

### Ajouter une séquence
1. Ajouter dans `FOLLOWUP_SEQUENCES`
2. Créer template dans `generate_email_body()`
3. Restart cron (automatique)

### Désactiver temporairement
```bash
crontab -e
# Commenter la ligne automated_trial_followup
```

## Métriques clés

- **Total trials** : Signups dans trial_signups_tracking.json
- **Followups sent** : Emails envoyés avec succès
- **Followups failed** : Échecs d'envoi
- **Sequences sent** : Détail par séquence (day1, day3, day7)

## Intégration avec conversion tracking

Le script vérifie automatiquement le flag `conversion_completed` :
- Si `true` → skip tous les emails (user a déjà converti)
- Si `false` → continue la séquence normalement

Synchronisation avec `/opt/claude-ceo/workspace/arkwatch/conversion/trial_tracker.py` qui met à jour ce flag.

## FAQ

**Q : Et si un user convertit entre J+3 et J+7 ?**
R : Le script check `conversion_completed` à chaque run. Si true, il skip J+7.

**Q : Limite d'emails par jour ?**
R : 30/jour via email_sender.py (warmup OVH). Les emails actionnaire sont exclus.

**Q : Retry si échec d'envoi ?**
R : Non, mais le log permet de voir les échecs. Prochaine exécution (6h) va re-tenter.

**Q : Peut-on tester sans envoyer d'emails ?**
R : Modifier le script pour print() au lieu de send_followup_email().

**Q : Personnalisation par use case ?**
R : Oui, fonction `extract_use_case()` détecte le use case et adapte le contenu.

## Prochaines améliorations

- [ ] A/B testing des subject lines
- [ ] Tracking opens/clicks (via tracking pixels)
- [ ] Segmentation par source (LinkedIn, HN, direct)
- [ ] Email différent si user actif vs inactif
- [ ] Personnalisation par vertical (SaaS, e-commerce, etc.)

---

**Status** : ✅ PROD READY
**Cron** : ✅ Actif (toutes les 6h)
**Tests** : ✅ Passés
**Date déploiement** : 2026-02-09
