# ArkWatch - Système de Nurturing Automatique Audit Gratuit

## Vue d'ensemble

Système d'emails automatiques en 3 étapes sur 7 jours pour convertir les leads d'audit gratuit en utilisateurs trial 14j.

**Objectif**: 10% conversion leads audit gratuit → trial 14j  
**Durée**: 7 jours  
**Fréquence**: Emails envoyés automatiquement toutes les heures (cron)

---

## Architecture

### Sources de leads

Le système agrège les leads de 3 sources:

1. **Form submissions** (`audit_gratuit_tracking.json`)
   - Formulaire principal "Réserver votre audit gratuit"
   - Contient: email, nom, stack, URL à auditer

2. **Exit-intent captures** (`audit_gratuit_exit_captures.json`)
   - Popup exit-intent sur page /audit-gratuit-monitoring.html
   - Contient: email uniquement

3. **Email-only captures** (`audit_gratuit_email_captures.json`)
   - Popup simple email capture
   - Contient: email uniquement

**Déduplication**: Un lead = 1 email unique (première occurrence conservée)

### Séquence d'emails

| Jour | Step ID | Sujet | Objectif | CTA |
|------|---------|-------|----------|-----|
| **J+2** | `day2_use_case_apm` | "Comment ArkWatch a détecté 3 bugs critiques en 48h" | Prouver la valeur via use case réel | Trial 14j |
| **J+4** | `day4_demo_loom` | "[90 secondes] Voyez ArkWatch surveiller vos URLs en temps réel" | Montrer l'interface (vidéo Loom) | Trial 14j + Watch demo |
| **J+7** | `day7_trial_urgency` | "Dernière chance: essai gratuit 14 jours ArkWatch Pro" | Urgence + FOMO + résultats audit | Trial 14j |

**Note**: J+0 (welcome email) est géré séparément au moment de la soumission du formulaire.

---

## Tracking & Analytics

### Email tracking

Chaque email contient:

1. **Tracking pixel** (ouvertures)
   - URL: `https://watch.arkforge.fr/track-email-open/nurturing_audit_{email}_{step_id}`
   - Permet de mesurer le taux d'ouverture par step

2. **Click tracking** (clics sur liens)
   - Format: `https://watch.arkforge.fr/track-click/nurturing_audit_{email}_{step_id}?url={destination}`
   - Tous les CTA (trial, demo Loom) sont trackés

### État du nurturing

**Fichier**: `/opt/claude-ceo/workspace/arkwatch/data/nurturing_audit_gratuit_state.json`

Structure:
```json
{
  "leads": {
    "user@example.com": {
      "sent_steps": ["day2_use_case_apm", "day4_demo_loom"],
      "history": [
        {
          "step": "day2_use_case_apm",
          "sent_at": "2026-02-09T10:00:00Z",
          "status": "sent"
        }
      ],
      "unsubscribed": false
    }
  },
  "metrics": {
    "total_sent": 150,
    "total_failed": 3,
    "by_step": {
      "day2_use_case_apm": 50,
      "day4_demo_loom": 50,
      "day7_trial_urgency": 50
    }
  },
  "last_run": "2026-02-11T00:00:00Z"
}
```

---

## Déploiement

### Installation

1. **Script Python**
   ```bash
   /opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py
   ```

2. **Installer le cron job**
   ```bash
   bash /opt/claude-ceo/workspace/arkwatch/automation/setup_nurturing_audit_gratuit_cron.sh
   ```

3. **Vérifier l'installation**
   ```bash
   crontab -l | grep nurturing_audit_gratuit
   ```

### Cron job

**Schedule**: Toutes les heures (à :00)  
**Commande**: `python3 nurturing_audit_gratuit.py`  
**Logs**: `/opt/claude-ceo/workspace/arkwatch/logs/nurturing_audit_gratuit.log`

---

## Utilisation

### Commandes

```bash
# Lancer manuellement (envoie emails réels)
python3 /opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py

# Mode dry-run (simulation, pas d'envoi)
python3 /opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py --dry-run

# Voir le statut du nurturing
python3 /opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py --status
```

### Output exemple (--status)

```
============================================================
ARKWATCH AUDIT GRATUIT NURTURING - STATUS
============================================================
Last run: 2026-02-11T00:00:00Z
Total sent: 150
Total failed: 3

By step:
  day2_use_case_apm: 50 sent
  day4_demo_loom: 50 sent
  day7_trial_urgency: 50 sent

Total leads (all sources): 60
Leads in nurturing: 50
  user1@example.com: 3/3 steps sent (day2_use_case_apm, day4_demo_loom, day7_trial_urgency)
  user2@example.com: 2/3 steps sent (day2_use_case_apm, day4_demo_loom)
  user3@example.com: 1/3 steps sent (day2_use_case_apm)
============================================================
```

---

## Monitoring & Métriques

### KPIs à suivre

| Métrique | Source | Objectif |
|----------|--------|----------|
| **Taux d'ouverture** | Tracking pixels | >30% par email |
| **Taux de clic** | Click tracking | >5% par email |
| **Conversion trial 14j** | `/data/trial_14d_signups.json` | >10% total |
| **Emails envoyés** | State file `metrics.total_sent` | 100% coverage |
| **Emails échoués** | State file `metrics.total_failed` | <1% |

### Logs

**Fichier**: `/opt/claude-ceo/workspace/arkwatch/logs/nurturing_audit_gratuit.log`

Contient:
- Timestamp de chaque run
- Nombre d'emails dus
- Résultats envoi (OK/FAILED)
- Erreurs SMTP

### Alertes

Si `metrics.total_failed > 10` → Alerter actionnaire (email système en panne)

---

## Optimisations futures

### Court terme (1-2 semaines)
- [ ] Créer vidéo Loom 90s (actuellement placeholder)
- [ ] A/B test sujets emails (variant J+2, J+4)
- [ ] Ajouter unsubscribe link dans footer

### Moyen terme (1 mois)
- [ ] Segmentation leads (source: exit-intent vs form complet)
- [ ] Personnalisation emails (nom, stack mentionné dans form)
- [ ] Split-test J+2 vs J+3 pour day2_use_case_apm

### Long terme (3 mois)
- [ ] Analyse cohortes (conversion par semaine)
- [ ] Machine learning: prédire probabilité conversion
- [ ] Dynamic content: adapter CTA selon comportement

---

## Troubleshooting

### Pas d'emails envoyés

1. **Vérifier cron job**
   ```bash
   crontab -l | grep nurturing_audit_gratuit
   ```

2. **Vérifier logs**
   ```bash
   tail -50 /opt/claude-ceo/workspace/arkwatch/logs/nurturing_audit_gratuit.log
   ```

3. **Tester manuellement**
   ```bash
   python3 /opt/claude-ceo/workspace/arkwatch/automation/nurturing_audit_gratuit.py --dry-run
   ```

### Emails échouent (SMTP errors)

1. **Vérifier credentials OVH**
   - Fichier: `/opt/claude-ceo/config/ovh_credentials.json`
   - Vérifier `smtp_username`, `smtp_password`

2. **Tester email_sender.py**
   ```bash
   python3 -c "from automation.email_sender import send_email; send_email('test@example.com', 'Test', 'Body test')"
   ```

3. **Vérifier quota OVH**
   - Max: 200 emails/jour
   - Vérifier `warmup_state.json` pour quota actuel

### Leads pas chargés

1. **Vérifier sources de données**
   ```bash
   cat /opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json | jq '.submissions | length'
   cat /opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_exit_captures.json | jq '.captures | length'
   ```

2. **Vérifier format timestamps**
   - Doit être ISO 8601: `2026-02-11T00:00:00Z`
   - Le script parse avec `datetime.fromisoformat()`

---

## Contact

**Équipe**: Worker Fondations (ArkForge CEO System)  
**Responsable**: CEO (via directives)  
**Support**: Actionnaire (apps.desiorac@gmail.com) pour blocages critiques

---

**Dernière mise à jour**: 2026-02-11  
**Version**: 1.0  
**Statut**: ✅ DEPLOYED
