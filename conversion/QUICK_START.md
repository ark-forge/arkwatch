# Quick Start - Conversion Leads ArkWatch

**Temps total: 30 min par lead**

## 🚀 Process en 5 étapes

### 1. Nouveau lead capturé (2 min)
```bash
# Vérifier nouveaux leads
cat /opt/claude-ceo/workspace/arkwatch/data/demo_leads.json
cat /opt/claude-ceo/workspace/arkwatch/data/leadgen_analytics.json
```

**Action**: Noter email + source dans `conversion_tracker.csv`

---

### 2. Email de suivi (5 min)
```bash
# Choisir template selon source
cat email_templates.md
```

**Templates disponibles**:
- Demo page → Template 1
- Pricing page → Template 2 (avec offre early bird)
- Trial signup → Template 3

**Action**: Copier-coller template, personnaliser [Prénom], envoyer < 24h

---

### 3. Créer trial guidé (10 min)
```bash
# Se connecter au serveur
ssh ubuntu@watch.arkforge.fr
cd /opt/arkwatch/api
source venv/bin/activate

# Créer trial user
python3 scripts/create_trial_user.py \
    --email prospect@company.com \
    --tier pro \
    --trial-days 14
```

**Retourne**: API Key + credentials

**Action**: Envoyer credentials par email (template dans trial_setup_guide.md)

---

### 4. Support pendant trial (14 jours)
**Check-ins à faire**:
- J+3: "Avez-vous pu tester ?"
- J+7: Template 4 (mid-trial check-in)
- J+10: "3 jours restants, questions ?"

**Démo optionnelle**: 30 min Zoom si demandée

---

### 5. Conversion payante (5 min)
```bash
# J+13: Envoyer email Template 5 (fin trial)
# Si prospect répond "OUI", générer facture:

cd /opt/claude-ceo/workspace/arkwatch/conversion

python3 stripe_invoice_script.py \
    --email prospect@company.com \
    --tier pro \
    --send-email
```

**Action**: Facture envoyée par Stripe automatiquement

---

## 📊 Tracking

**Mettre à jour à chaque étape**: `conversion_tracker.csv`

**Statuts**:
- `qualified` → Email validé
- `contacted` → Email envoyé
- `trial_active` → Trial créé
- `invoice_sent` → Facture envoyée
- `converted_paid` → Client payant ✅

---

## 🆘 Aide

| Besoin | Fichier |
|--------|---------|
| Templates emails | `email_templates.md` |
| Checklist complète | `onboarding_checklist.md` |
| Créer trial | `trial_setup_guide.md` |
| Générer facture | `stripe_invoice_script.py` |

---

## 🎯 Objectifs

| Métrique | Cible |
|----------|-------|
| Temps réponse lead | < 24h |
| Taux activation trial | > 50% |
| Taux conversion | > 20% |
| Temps moyen conversion | < 21 jours |

---

**Note**: Process 100% manuel pour commencer. Automatisation après 5+ clients.

*Quick Start créé par Worker Fondations - Task #20260903*
