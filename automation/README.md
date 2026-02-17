# ArkWatch Automation Scripts

Scripts d'automatisation pour ArkWatch.

## free_trial_nurture.py

Script de nurturing pour les utilisateurs en période d'essai gratuit (6 mois).

### Fonctionnalités

- **Phase 1 (J+0)**: Email de bienvenue avec guide de démarrage
- **Phase 2 (J+2)**: Rappel d'activation si compte non activé
- **Phase 3 (J+7)**: Tips & astuces si compte activé mais pas de surveillance créée
- **Phase 4 (J+150, J+165, J+175)**: Rappels de conversion avant fin de période d'essai

### Conformité RGPD

- Consentement implicite lors de l'inscription au free trial
- Lien de désinscription dans chaque email
- Fréquence limitée (pas de spam)
- Respect du droit de désinscription

### Utilisation

```bash
# Exécution manuelle
python3 /opt/claude-ceo/workspace/arkwatch/automation/free_trial_nurture.py

# Via cron (recommandé: 1x/jour à 10h)
0 10 * * * python3 /opt/claude-ceo/workspace/arkwatch/automation/free_trial_nurture.py
```

### Fichiers

- **Entrée**: `/opt/claude-ceo/workspace/arkwatch/data/free_trial_signups.json`
- **État**: `/opt/claude-ceo/workspace/arkwatch/data/nurture_log.json`
- **Logs**: `/opt/claude-ceo/workspace/arkwatch/logs/nurture.log`

### Logique de détection

Le script détecte automatiquement:
- Si l'utilisateur a activé son compte (présence dans api_keys.json)
- Si l'utilisateur a créé des surveillances (présence dans watches.json)
- Les emails déjà envoyés (évite les doublons)

### Phases détaillées

#### Phase 1: Signup (J+0)
- Email de bienvenue
- Guide de démarrage rapide
- Liens vers documentation
- Information sur la durée de l'essai

#### Phase 2: Activation (J+2)
- Rappel d'activation si pas encore de compte
- Procédure d'activation en 2 minutes
- Exemples d'utilisation

#### Phase 3: Engagement (J+7)
- Astuces pour optimiser les surveillances
- Configuration des intervalles
- Utilisation de l'IA
- Cas d'usage concrets

#### Phase 4: Conversion (J+150, J+165, J+175)
- Rappel de fin d'essai
- Présentation des formules payantes
- FAQ sur l'abonnement
- Incitation à la conversion

### Statistiques

Le script génère des statistiques à chaque exécution:
- Nombre d'emails envoyés par phase
- Nombre d'utilisateurs traités
- Nombre d'erreurs

### Sécurité

- Validation des emails
- Atomic writes pour les fichiers JSON
- Gestion des erreurs
- Timeout sur les envois d'emails

### Extensibilité

Pour ajouter une nouvelle phase:

1. Créer une fonction `send_PHASE_email(email, days_since_signup)`
2. Ajouter la logique dans `process_signup()`
3. Mettre à jour les statistiques dans `main()`

### Notes

- Le script est idempotent (peut être exécuté plusieurs fois sans effet de bord)
- Les emails ne sont envoyés qu'une seule fois par phase
- Les utilisateurs ayant expiré leur essai sont ignorés
- Les erreurs sont loggées mais n'interrompent pas le traitement
