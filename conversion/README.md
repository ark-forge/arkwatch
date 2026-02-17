# Workflow Manuel Conversion Leads→Clients ArkWatch

**Créé**: 2026-02-09
**Objectif**: Processus manuel reproductible (~30min/lead) pour convertir leads capturés en clients payants
**Status**: Ready to use

---

## 📋 Vue d'ensemble

Ce dossier contient tout le nécessaire pour convertir manuellement les leads en clients payants :

1. **Templates emails** personnalisés par type de lead
2. **Checklist onboarding** manuel avec support 1-to-1
3. **Script génération factures** Stripe Invoice (pas checkout)
4. **Tracking spreadsheet** leads→conversion

---

## 🎯 Flux de Conversion (30min/lead)

```
LEAD CAPTURÉ (demo/pricing)
    ↓
[1] Email de suivi personnalisé (5min)
    ↓
[2] Réponse prospect + questions
    ↓
[3] Créer trial guidé manuel (10min)
    ↓
[4] Démo 1-to-1 Zoom (30min optionnel)
    ↓
[5] Support direct pendant trial (14j)
    ↓
[6] Fin trial → Génération facture Stripe (5min)
    ↓
[7] Paiement → Activation client (2min)
    ↓
✅ CONVERSION COMPLÈTE
```

**Temps total**: 30min actif + 30min démo optionnelle

---

## 📁 Fichiers dans ce dossier

| Fichier | Description |
|---------|-------------|
| `email_templates.md` | Templates emails par type de lead |
| `onboarding_checklist.md` | Checklist étape par étape pour onboarding manuel |
| `stripe_invoice_script.py` | Script génération facture Stripe Invoice |
| `conversion_tracker.csv` | Spreadsheet tracking leads→conversion |
| `trial_setup_guide.md` | Guide création trial guidé manuel |
| `demo_script.md` | Script pour démo 1-to-1 Zoom |

---

## 🚀 Quick Start

### Étape 1: Nouveau lead capturé
```bash
# Vérifier nouveaux leads
cat /opt/claude-ceo/workspace/arkwatch/data/demo_leads.json
cat /opt/claude-ceo/workspace/arkwatch/data/leadgen_analytics.json
```

### Étape 2: Envoyer email de suivi
```bash
# Utiliser template approprié
cat conversion/email_templates.md

# Envoyer email personnalisé (Gmail, Outlook, etc.)
# → Copier-coller template
# → Personnaliser nom + contexte
# → Envoyer sous 24h
```

### Étape 3: Créer trial guidé
```bash
# Suivre checklist
cat conversion/onboarding_checklist.md

# Créer compte trial manuellement
# → Dashboard ArkWatch
# → Créer user avec email prospect
# → Activer trial 14j
# → Envoyer credentials par email
```

### Étape 4: Démo 1-to-1 (optionnel)
```bash
# Utiliser script démo
cat conversion/demo_script.md

# Zoom 30min pour montrer:
# → Setup premier monitor
# → Configuration alertes
# → Cas d'usage spécifique du prospect
```

### Étape 5: Fin trial → Facture
```bash
# Générer facture Stripe
python3 conversion/stripe_invoice_script.py \
    --email prospect@company.com \
    --tier pro \
    --send-email

# → Facture envoyée par Stripe automatiquement
# → Prospect paie via lien dans email
# → Webhook active abonnement
```

### Étape 6: Tracking
```bash
# Mettre à jour spreadsheet
# conversion_tracker.csv
# → Ajouter ligne avec statut
```

---

## 📊 KPIs de Conversion

| Métrique | Objectif |
|----------|----------|
| Temps de réponse lead | < 24h |
| Taux d'activation trial | > 50% |
| Démos réalisées | > 30% des leads |
| Taux conversion trial→payant | > 20% |
| Temps moyen de conversion | < 21 jours |

---

## ⚠️ Notes Importantes

1. **Pas d'automatisation** : Ce workflow est 100% manuel pour commencer
2. **Support direct** : Répondre à tous les emails sous 4h
3. **Personnalisation** : Adapter templates selon contexte du lead
4. **Suivi** : Logger toutes les interactions dans conversion_tracker.csv
5. **Stripe Invoice** : Pas de checkout automatique, factures manuelles

---

## 🔄 Evolution Future

Une fois 5+ clients payants :
- Automatiser email de suivi (n+1)
- Intégrer trial signup automatique
- Ajouter onboarding par email automatisé
- Migrer vers Stripe Checkout automatique

**Pour l'instant : Manuel = mieux pour apprendre et itérer vite**

---

## 📞 Support

En cas de questions pendant conversion :
- **Technique** : Vérifier `/opt/claude-ceo/docs/STRIPE_CHECKOUT_INFRASTRUCTURE.md`
- **Business** : Consulter CEO via task queue
- **Urgence** : Email actionnaire directement

---

*Workflow créé par Worker Fondations - Task #20260903*
