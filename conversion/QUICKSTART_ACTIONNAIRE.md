# 🚀 QUICKSTART ACTIONNAIRE - Monitoring Conversion 55 CTOs

**Task ID**: 122
**Deadline**: 48h (2026-02-12 23:59 UTC)
**Objectif**: 1-3 CTOs convertis en appel qualificatif

---

## ⚡ SETUP RAPIDE (5 minutes)

### Étape 1: Installer dépendance OVH SMS
```bash
pip3 install ovh
```

### Étape 2: Activer monitoring automatique
```bash
cd /opt/claude-ceo/workspace/arkwatch/conversion
./setup_monitoring_cron.sh
```

**Résultat**: Script tourne automatiquement toutes les 5 minutes

### Étape 3: Vérifier état
```bash
cat /opt/claude-ceo/workspace/arkwatch/conversion/hot_leads_realtime.json
```

---

## 📱 QUAND VOUS RECEVEZ UN SMS

### Format SMS reçu
```
🔥 HOT LEAD DÉTECTÉ

Signal: Visite page audit > 90s

Entreprise: Pennylane
Secteur: FinTech
Pain: Coût Datadog explose

APPELER MAINTENANT
Script: workspace/croissance/...

ArkForge CEO
```

### ✅ ACTION IMMÉDIATE (5-15 min max)

1. **Ouvrir script appel**
   ```bash
   cat /opt/claude-ceo/workspace/croissance/ACTION_ACTIONNAIRE_COLD_CALL_TOP3_HOT_WEB_20261133.md
   ```

2. **Identifier contact exact**
   - Lire fichier prospects:
     ```bash
     grep -A 10 "Pennylane" /opt/claude-ceo/workspace/croissance/PROSPECTS_30_CTOS_SCALEUPS_TASK_20261240.json
     ```
   - Récupérer: Nom CTO, téléphone, email, pain point exact

3. **APPELER IMMÉDIATEMENT**
   - Fenêtre optimale: **5-15 min** après signal
   - Utiliser script d'accroche personnalisé

4. **Logger résultat**
   ```bash
   echo '{"date":"2026-02-10","entreprise":"Pennylane","signal":"page_visit","resultat":"converti","notes":"..."}' >> /opt/claude-ceo/workspace/arkwatch/conversion/call_log.jsonl
   ```

---

## 🎯 LES 3 SIGNAUX HOT

### Signal 1: Visite page > 90s ⏱️
- **Signification**: Lecture approfondie de la page audit gratuit
- **Timing optimal**: Appeler dans les 5-15 min
- **Accroche**: "Je vois que vous étudiez notre audit gratuit Datadog..."

### Signal 2: Clic CTA 'Réserver audit' 🔥
- **Signification**: Action concrète, prêt à s'engager
- **Timing optimal**: Appeler IMMÉDIATEMENT (< 5 min)
- **Accroche**: "Vous venez de cliquer sur 'Réserver audit' - je peux vous briefer maintenant?"

### Signal 3: Ouverture email J+1/J+2 📧
- **Signification**: Réflexion + retour = moment optimal
- **Timing optimal**: Appeler dans l'heure
- **Accroche**: "Vous avez rouvert mon email ce matin - des questions sur l'audit gratuit?"

---

## 📊 MONITORING EN TEMPS RÉEL

### Dashboard CLI
```bash
# Voir état actuel
watch -n 30 'cat /opt/claude-ceo/workspace/arkwatch/conversion/hot_leads_realtime.json'

# Voir logs monitoring
tail -f /opt/claude-ceo/workspace/arkwatch/conversion/monitoring.log

# Voir alertes envoyées
cat /opt/claude-ceo/workspace/arkwatch/conversion/conversion_alerts.jsonl | tail -10
```

### Statistiques rapides
```bash
cd /opt/claude-ceo/workspace/arkwatch/conversion

# Total signaux détectés
cat hot_leads_realtime.json | grep "hot_signals_detected"

# Derniers leads HOT
cat hot_leads_realtime.json | grep -A 5 "leads"

# SMS envoyés aujourd'hui
cat conversion_alerts.jsonl | grep "$(date +%Y-%m-%d)" | wc -l
```

---

## 🛠️ TROUBLESHOOTING

### Problème: Aucun signal détecté après 24h

**Diagnostic**:
```bash
# Vérifier trafic réel sur page
tail -100 /opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_visitors.jsonl

# Si vide → tracking web pas actif
ls -la /opt/claude-ceo/workspace/arkwatch/data/
```

**Solution**:
1. Vérifier que endpoint `/api/track_visitor_audit_gratuit` est déployé
2. Vérifier intégration JavaScript dans `/audit-gratuit-monitoring.html`
3. Tester manuellement:
   ```bash
   curl -X POST https://arkforge.fr/api/track_visitor_audit_gratuit \
     -H "Content-Type: application/json" \
     -d '{"visitor_id":"test123","event":"pageview"}'
   ```

### Problème: SMS non reçu

**Diagnostic**:
```bash
# Vérifier credentials OVH
cat /opt/claude-ceo/config/ovh_credentials.json

# Vérifier dernière erreur
cat /opt/claude-ceo/workspace/arkwatch/conversion/conversion_alerts.jsonl | tail -5
```

**Solution**:
1. Tester envoi SMS manuel:
   ```bash
   cd /opt/claude-ceo/automation
   python3 -c "
   import ovh
   import json
   with open('/opt/claude-ceo/config/ovh_credentials.json') as f:
       creds = json.load(f)
   client = ovh.Client(**creds)
   svc = client.get('/sms')[0]
   client.post(f'/sms/{svc}/jobs', sender='ArkForge', message='Test', receivers=['+33749879812'])
   "
   ```

2. Si erreur credentials → Regénérer tokens OVH console

---

## 📈 OBJECTIFS TASK #122

### Minimum viable
- ✅ Monitoring actif (toutes les 5 min)
- ✅ SMS envoyé dès signal détecté
- ⏳ **1 CTO converti** en appel qualificatif (48h)

### Target optimal
- 🎯 **3 CTOs convertis** en appels qualificatifs
- 🎯 Taux détection ≥ 80% des signaux HOT
- 🎯 Temps réponse < 5 min (signal → SMS)

### Métriques clés
```json
{
  "hot_signals_detected": 12,    // Total signaux détectés
  "conversion_alerts_sent": 8,   // SMS envoyés actionnaire
  "calls_made": 8,               // Appels réalisés
  "calls_qualified": 3,          // Appels convertis en prospect qualifié
  "conversion_rate": 37.5        // % CTOs → Clients (objectif: 3-10%)
}
```

---

## 🎬 NEXT STEPS SI CONVERSION RÉUSSIE

### CTO converti → Onboarding immédiat

1. **Créer compte Stripe**
   ```bash
   cd /opt/claude-ceo/workspace/arkwatch
   python3 scripts/create_stripe_customer.py \
     --email="cto@pennylane.com" \
     --entreprise="Pennylane" \
     --plan="trial_14d"
   ```

2. **Envoyer email onboarding**
   - Template: `/opt/claude-ceo/workspace/arkwatch/conversion/email_templates.md`
   - Inclure: Credentials trial, guide setup monitoring, contact support

3. **Planifier follow-up J+3**
   - Check usage trial
   - Questions techniques
   - Conversion trial → payant

---

## 📞 SUPPORT

### Logs complets
- **Monitoring**: `/opt/claude-ceo/workspace/arkwatch/conversion/monitoring.log`
- **Alertes**: `/opt/claude-ceo/workspace/arkwatch/conversion/conversion_alerts.jsonl`
- **État temps réel**: `/opt/claude-ceo/workspace/arkwatch/conversion/hot_leads_realtime.json`

### Commandes utiles
```bash
# Stop monitoring temporairement
crontab -l | grep -v "monitor_conversion_realtime" | crontab -

# Restart monitoring
cd /opt/claude-ceo/workspace/arkwatch/conversion
./setup_monitoring_cron.sh

# Reset état (testing)
rm /opt/claude-ceo/workspace/arkwatch/conversion/hot_leads_realtime.json
python3 monitor_conversion_realtime.py
```

---

**Gardien Task #122** - Infrastructure prête
**Status**: ✅ Production ready - Attente premiers signaux
**SMS Alert**: +33749879812 (actif)
