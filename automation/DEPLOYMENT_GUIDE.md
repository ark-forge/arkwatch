# Guide de Déploiement - Free Trial Nurture System

## 🚀 Déploiement Rapide

### Étape 1: Vérification des prérequis

```bash
cd /opt/claude-ceo/workspace/arkwatch

# Vérifier que les fichiers sont présents
ls -l automation/free_trial_nurture.py
ls -l automation/check_nurture_status.py
ls -l automation/setup_cron.sh
```

### Étape 2: Test du système

```bash
# Test syntaxe Python
python3 -m py_compile automation/free_trial_nurture.py

# Test unitaire (optionnel - tests mocked)
python3 automation/test_nurture.py

# Status actuel
python3 automation/check_nurture_status.py
```

### Étape 3: Exécution manuelle test

```bash
# Première exécution (mode test)
python3 automation/free_trial_nurture.py

# Vérifier les logs
tail -50 logs/nurture.log

# Vérifier le fichier d'état créé
cat data/nurture_log.json | jq
```

### Étape 4: Automatisation (Cron)

```bash
# Setup cron pour exécution quotidienne à 10h UTC
sudo bash automation/setup_cron.sh

# Vérifier que le cron est actif
crontab -l | grep nurture

# Vérifier les logs cron (après 24h)
tail -f logs/nurture_cron.log
```

## 📋 Checklist de Déploiement

- [ ] Fichiers présents dans `/opt/claude-ceo/workspace/arkwatch/automation/`
- [ ] Dossier `logs/` créé
- [ ] Test syntaxe Python OK
- [ ] Test unitaire OK (optionnel)
- [ ] Exécution manuelle OK
- [ ] Logs générés correctement
- [ ] Fichier `nurture_log.json` créé
- [ ] Cron configuré
- [ ] Vérification 24h après (logs cron)

## 🔍 Monitoring Post-Déploiement

### Jour 1
```bash
# Vérifier exécution
tail -50 logs/nurture.log

# Vérifier emails envoyés
python3 automation/check_nurture_status.py
```

### Jour 7
```bash
# Statistiques hebdomadaires
python3 automation/check_nurture_status.py

# Vérifier taux d'activation
# Target: >60% des signups ont activé leur compte
```

### Jour 30
```bash
# Analyse complète du funnel
python3 automation/check_nurture_status.py

# Analyser les métriques:
# - Signup → Activation: >60%
# - Activation → Engagement: >40%
# - Engagement → Rétention: >30%
```

## 🛠️ Commandes Utiles

### Logs
```bash
# Logs d'exécution
tail -f logs/nurture.log

# Logs cron
tail -f logs/nurture_cron.log

# Chercher erreurs
grep -i error logs/nurture.log
```

### Status
```bash
# Status complet
python3 automation/check_nurture_status.py

# Signups récents
cat data/free_trial_signups.json | jq

# Emails envoyés
cat data/nurture_log.json | jq
```

### Maintenance
```bash
# Exécution manuelle
python3 automation/free_trial_nurture.py

# Désactiver cron temporairement
crontab -e  # Commenter la ligne

# Réactiver cron
crontab -e  # Décommenter la ligne
```

## 🔧 Dépannage

### Problème: Aucun email envoyé

**Symptôme**: Logs montrent "skipped" pour tous les signups

**Causes possibles**:
1. Tous les emails ont déjà été envoyés (vérifier `nurture_log.json`)
2. Pas de nouveaux signups (vérifier `free_trial_signups.json`)
3. Essais expirés (>180 jours)

**Solution**:
```bash
# Vérifier état
python3 automation/check_nurture_status.py

# Inspecter nurture_log
cat data/nurture_log.json | jq '.[] | {email: .email, events: .events | length}'
```

### Problème: Erreurs d'envoi email

**Symptôme**: Logs montrent "Email failed"

**Causes possibles**:
1. email_sender.py non accessible
2. Credentials SMTP invalides
3. Timeout

**Solution**:
```bash
# Tester email_sender directement
python3 /opt/claude-ceo/automation/email_sender.py \
  "test@example.com" \
  "Test" \
  "Test body"

# Vérifier logs détaillés
tail -100 logs/nurture.log | grep -A5 "Email failed"
```

### Problème: Cron ne s'exécute pas

**Symptôme**: Pas de logs dans `nurture_cron.log`

**Causes possibles**:
1. Cron non configuré
2. Cron désactivé
3. Erreur de path

**Solution**:
```bash
# Vérifier cron
crontab -l

# Vérifier logs système
sudo tail -f /var/log/syslog | grep CRON

# Tester manuellement avec la même commande
cd /opt/claude-ceo/workspace/arkwatch && python3 automation/free_trial_nurture.py
```

## 📊 Métriques de Succès

### Semaine 1
- ✅ Au moins 1 email de bienvenue envoyé
- ✅ Pas d'erreur critique dans les logs
- ✅ Cron s'exécute quotidiennement

### Mois 1
- ✅ Taux d'activation >60%
- ✅ Taux d'engagement >40%
- ✅ 0 plainte spam

### Trimestre 1
- ✅ Taux de conversion >20%
- ✅ Système stable (uptime >99%)
- ✅ Optimisation basée sur données

## 🔒 Sécurité & Conformité

### Vérifications RGPD
- [ ] Lien de désinscription dans chaque email
- [ ] Fréquence d'envoi limitée (max 6 emails sur 6 mois)
- [ ] Pas de données sensibles dans logs
- [ ] Consentement implicite à l'inscription

### Vérifications Techniques
- [ ] Fichiers JSON protégés (chmod 600 pour données)
- [ ] Logs rotationnés (logrotate)
- [ ] Pas de secrets en clair dans le code
- [ ] Gestion des erreurs sans exposition de données

## 📞 Support

### Questions Techniques
- **Worker Gardien**: Responsable du système
- **Logs**: `/opt/claude-ceo/workspace/arkwatch/logs/nurture.log`
- **Documentation**: `/opt/claude-ceo/workspace/arkwatch/docs/FREE_TRIAL_NURTURE_SYSTEM.md`

### Questions Business
- **CEO**: Validation des modifications de contenu/stratégie
- **Actionnaire**: Décisions structurantes

## 📝 Changelog Post-Déploiement

Format pour documenter les changements:

```
## YYYY-MM-DD - vX.Y.Z

### Added
- Nouvelle fonctionnalité

### Changed
- Modification de comportement

### Fixed
- Correction de bug

### Metrics
- Metric 1: XX%
- Metric 2: YY
```

---

**Date de création**: 2026-02-09
**Version**: 1.0.0
**Responsable**: Worker Gardien
**Status**: ✅ Prêt pour déploiement
