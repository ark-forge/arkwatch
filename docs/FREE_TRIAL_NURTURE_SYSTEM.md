# Système de Nurturing Free Trial - ArkWatch

## 📋 Vue d'ensemble

Système automatisé de nurturing pour accompagner les utilisateurs pendant leur période d'essai gratuit de 6 mois et maximiser la conversion en clients payants.

## 🎯 Objectifs

1. **Activation**: Convertir les signups en utilisateurs actifs (création compte + API key)
2. **Engagement**: Inciter à créer des surveillances et utiliser le produit
3. **Éducation**: Fournir tips et best practices pour maximiser la valeur
4. **Conversion**: Transformer les utilisateurs d'essai en clients payants

## 📊 Phases de Nurturing

### Phase 1: Bienvenue (J+0)
- **Trigger**: Signup immédiat
- **Email**: Bienvenue + guide de démarrage
- **Contenu**:
  - Confirmation de l'inscription
  - Durée de l'essai (6 mois)
  - Étapes d'activation du compte
  - Liens vers documentation
- **Objectif**: Premier contact positif, clarifier les prochaines étapes

### Phase 2: Activation (J+2)
- **Trigger**: 2 jours après signup, si pas de compte activé
- **Email**: Rappel d'activation
- **Contenu**:
  - Rappel que l'essai est déjà actif
  - Guide d'activation en 2 minutes
  - Exemples d'utilisation
  - Offre d'aide
- **Objectif**: Réduire le taux d'abandon post-signup

### Phase 3: Engagement (J+7)
- **Trigger**: 7 jours après signup, si compte activé mais pas de surveillance
- **Email**: Tips & astuces
- **Contenu**:
  - 3 astuces pour optimiser ArkWatch
  - Configuration des intervalles
  - Utilisation de l'IA
  - Cas d'usage concrets
- **Objectif**: Augmenter l'engagement et l'utilisation du produit

### Phase 4: Conversion (J+150, J+165, J+175)
- **Trigger**: 3 rappels avant fin d'essai (30j, 15j, 5j restants)
- **Email**: Rappel fin d'essai + offres
- **Contenu**:
  - Récapitulatif de l'essai
  - Présentation des formules payantes (Starter/Pro/Business)
  - FAQ sur l'abonnement
  - Call-to-action vers page pricing
- **Objectif**: Convertir en client payant

## 🏗️ Architecture

```
free_trial_signups.json (source)
           ↓
   free_trial_nurture.py (traitement)
           ↓
    ┌──────┴──────┐
    ↓             ↓
nurture_log.json  email_sender.py
  (état)          (envoi)
```

### Fichiers Clés

| Fichier | Rôle | Format |
|---------|------|--------|
| `free_trial_signups.json` | Liste des signups | JSON array |
| `nurture_log.json` | Historique des emails envoyés | JSON array |
| `api_keys.json` | Détection comptes activés | JSON array |
| `watches.json` | Détection surveillances créées | JSON array |
| `nurture.log` | Logs d'exécution | Text |

## 🔄 Flux d'Exécution

```
1. Charger free_trial_signups.json
2. Pour chaque signup:
   a. Calculer jours depuis inscription
   b. Vérifier si essai expiré → skip
   c. Charger historique nurture_log
   d. Détecter statut compte (activé? surveillances?)
   e. Déterminer phase appropriée
   f. Vérifier si email déjà envoyé → skip
   g. Envoyer email
   h. Logger dans nurture_log
3. Générer statistiques
4. Logger résumé
```

## 🔒 Conformité RGPD

### Consentement
- ✅ Consentement implicite lors du signup au free trial
- ✅ Information claire sur les communications pendant l'essai
- ✅ Lien de désinscription dans chaque email

### Droits des utilisateurs
- ✅ Droit de désinscription (lien dans chaque email)
- ✅ Droit à l'oubli (via API `/api/v1/auth/delete-account`)
- ✅ Accès aux données (nurture_log.json consultable)

### Sécurité
- ✅ Pas de données sensibles dans les logs
- ✅ Emails stockés en clair uniquement dans fichiers protégés (600)
- ✅ Atomic writes pour éviter corruption de données

## 📈 Métriques & KPIs

### Métriques de suivi

| Métrique | Description | Source |
|----------|-------------|--------|
| Signup → Activation | % signups qui activent compte | api_keys.json |
| Activation → Engagement | % activés qui créent surveillance | watches.json |
| Engagement → Rétention | % engagés qui restent actifs | watches.json (last_check) |
| Rétention → Conversion | % qui souscrivent après essai | payments.json |

### Objectifs cibles

- **Activation**: >60% (signups → comptes activés)
- **Engagement**: >40% (activés → surveillance créée)
- **Rétention**: >30% (engagés → utilisation régulière)
- **Conversion**: >20% (essai → payant)

## 🛠️ Installation & Configuration

### 1. Installation

```bash
# Déjà installé dans:
/opt/claude-ceo/workspace/arkwatch/automation/free_trial_nurture.py

# Rendre exécutable
chmod +x /opt/claude-ceo/workspace/arkwatch/automation/free_trial_nurture.py
```

### 2. Test

```bash
# Test syntaxe
python3 -m py_compile automation/free_trial_nurture.py

# Test complet (sans envoyer emails)
python3 automation/test_nurture.py
```

### 3. Exécution manuelle

```bash
cd /opt/claude-ceo/workspace/arkwatch
python3 automation/free_trial_nurture.py
```

### 4. Automatisation (cron)

```bash
# Setup cron (1x/jour à 10h UTC)
sudo bash automation/setup_cron.sh

# Vérifier cron
crontab -l | grep nurture

# Logs cron
tail -f logs/nurture_cron.log
```

## 📊 Monitoring

### Logs

```bash
# Logs d'exécution
tail -f /opt/claude-ceo/workspace/arkwatch/logs/nurture.log

# Logs cron
tail -f /opt/claude-ceo/workspace/arkwatch/logs/nurture_cron.log

# Historique des emails envoyés
cat /opt/claude-ceo/workspace/arkwatch/data/nurture_log.json | jq
```

### Statistiques

À chaque exécution, le script génère:
- Nombre total de signups traités
- Emails envoyés par phase (welcome, activation, engagement, conversion)
- Signups ignorés (raisons)
- Erreurs rencontrées

### Alertes

Créer des alertes si:
- `errors > 5` dans une exécution
- `welcome_sent = 0` pendant 3 jours consécutifs (pas de nouveaux signups)
- `conversion_reminder_sent = 0` alors que signups > 150 jours (problème de détection)

## 🔧 Maintenance

### Tâches quotidiennes
- ✅ Automatiques via cron (aucune action requise)

### Tâches hebdomadaires
- Vérifier logs pour erreurs
- Analyser taux d'activation/engagement
- Ajuster contenu emails si faible conversion

### Tâches mensuelles
- Analyser métriques complètes (activation → conversion)
- A/B test sur contenu emails
- Optimiser timing des phases

## 🚀 Évolutions Futures

### Court terme (1-2 mois)
- [ ] A/B testing sur sujets d'emails
- [ ] Personnalisation basée sur source/campaign
- [ ] Email de réactivation pour utilisateurs inactifs

### Moyen terme (3-6 mois)
- [ ] Segmentation par comportement (power users vs occasionnels)
- [ ] Intégration avec analytics pour scoring d'engagement
- [ ] Webhook pour events en temps réel (activation, première surveillance)

### Long terme (6-12 mois)
- [ ] Machine learning pour prédiction de conversion
- [ ] Personnalisation dynamique du timing (pas de J fixe)
- [ ] Multicanal (email + push + in-app)

## 📞 Support

### Questions fréquentes

**Q: Combien d'emails reçoit un utilisateur?**
R: Maximum 6 emails sur 6 mois (welcome + activation + engagement + 3x conversion).

**Q: Peut-on désactiver le nurturing?**
R: Oui, supprimer/commenter la ligne cron. Les utilisateurs peuvent aussi se désinscrire individuellement.

**Q: Les emails sont-ils testés?**
R: Oui, via `test_nurture.py`. Les emails réels peuvent être testés avec un compte test.

**Q: Que se passe-t-il si l'envoi échoue?**
R: L'erreur est loggée, l'email sera retenté à la prochaine exécution (si toujours dans la fenêtre temporelle).

### Contact

- **Worker Gardien**: Responsable technique du système
- **CEO**: Approbation des modifications de contenu/stratégie
- **Actionnaire**: Validation des changements structurants

## 📝 Changelog

### 2026-02-09 - v1.0.0 (INITIAL)
- ✅ Création du système de nurturing
- ✅ 4 phases implémentées (bienvenue, activation, engagement, conversion)
- ✅ Conformité RGPD
- ✅ Tests unitaires
- ✅ Documentation complète
- ✅ Setup cron

---

**Statut**: 🟢 OPÉRATIONNEL
**Dernière mise à jour**: 2026-02-09
**Responsable**: Worker Gardien
