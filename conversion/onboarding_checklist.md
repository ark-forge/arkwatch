# Checklist Onboarding Manuel - ArkWatch

**Créé**: 2026-02-09
**Usage**: Suivre étape par étape pour chaque nouveau lead
**Temps estimé**: ~30 min par lead

---

## 📋 Checklist Complète (Cocher au fur et à mesure)

### Phase 1: Qualification Lead (5 min)

- [ ] **Vérifier la source du lead**
  - Demo page ?
  - Pricing page ?
  - Trial signup ?
  - Autre (LinkedIn, Twitter, etc.) ?

- [ ] **Valider l'email**
  - ✅ Email professionnel (pas @gmail, @yahoo) ?
  - ✅ Domaine existant ?
  - ❌ Pas un email de test ?

- [ ] **Extraire le contexte**
  - Referer URL (d'où vient le lead) ?
  - Source tracking (utm_source, utm_campaign) ?
  - Timestamp de capture ?

- [ ] **Logger dans conversion_tracker.csv**
  - Ajouter ligne avec : email, source, date, statut="qualified"

---

### Phase 2: Premier Contact (5 min)

- [ ] **Choisir le template email approprié**
  - Demo page → Template 1
  - Pricing page → Template 2
  - Trial signup → Template 3

- [ ] **Personnaliser le template**
  - Remplacer [Prénom] (extraire de l'email)
  - Adapter le contexte selon source
  - Mentionner un détail spécifique si possible

- [ ] **Envoyer l'email sous 24h**
  - Via Gmail/Outlook perso
  - Object clair et accrocheur
  - Inclure signature avec lien https://arkforge.fr

- [ ] **Logger l'envoi**
  - Mettre à jour conversion_tracker.csv : statut="contacted"
  - Noter la date et l'heure d'envoi

---

### Phase 3: Attente Réponse (Variable)

- [ ] **Attendre réponse du prospect (1-3 jours)**
  - Si réponse positive → Passer à Phase 4
  - Si pas de réponse J+3 → Envoyer relance soft

- [ ] **Relance J+3 (si pas de réponse)**
  - Template court : "Bonjour [Prénom], avez-vous eu le temps de lire mon email précédent ?"
  - Proposer démo rapide 15 min

- [ ] **Logger la réponse**
  - Mettre à jour conversion_tracker.csv : statut="replied" ou "no_reply"

---

### Phase 4: Création Trial Guidé (10 min)

#### Option A: Trial 14j automatique (via landing page)
- [ ] **Envoyer lien trial signup**
  - https://arkforge.fr/trial-14d.html?plan=pro
  - Mentionner : "No CB required, 14 jours gratuits"

#### Option B: Trial manuel (création compte backend)
- [ ] **Créer compte user manuellement**
  ```bash
  # Se connecter au serveur ArkWatch
  ssh ubuntu@watch.arkforge.fr

  # Activer environnement Python
  cd /opt/arkwatch/api
  source venv/bin/activate

  # Créer user via script admin
  python3 scripts/create_trial_user.py \
      --email prospect@company.com \
      --tier pro \
      --trial-days 14

  # Script retourne API key + credentials
  ```

- [ ] **Envoyer credentials par email**
  - API Key
  - Dashboard URL : https://watch.arkforge.fr/dashboard
  - Documentation : https://arkforge.fr/docs
  - Date de fin du trial

- [ ] **Logger la création trial**
  - Mettre à jour conversion_tracker.csv : statut="trial_active"
  - Noter date de début et date de fin trial

---

### Phase 5: Démo 1-to-1 (Optionnel, 30 min)

- [ ] **Proposer démo Zoom**
  - "Besoin d'un walkthrough de 15 min ?"
  - Envoyer lien Calendly ou proposer créneaux

- [ ] **Préparer la démo**
  - Lire trial_setup_guide.md
  - Préparer exemples de monitors pertinents pour le cas d'usage

- [ ] **Réaliser la démo Zoom**
  - Suivre le script dans demo_script.md
  - Montrer : création monitor, configuration alertes, détection changements
  - Répondre aux questions

- [ ] **Follow-up post-démo**
  - Envoyer recap par email (résumé de ce qu'on a vu)
  - Partager ressources (docs, vidéos)

- [ ] **Logger la démo**
  - Mettre à jour conversion_tracker.csv : demo_done="yes"

---

### Phase 6: Support Pendant Trial (14 jours)

- [ ] **Check-in J+3**
  - Email rapide : "Avez-vous pu créer votre premier monitor ?"
  - Proposer aide si besoin

- [ ] **Check-in J+7**
  - Utiliser Template 4 (Mid-Trial Check-in)
  - Identifier blocages éventuels

- [ ] **Check-in J+10**
  - Email : "3 jours restants, des questions ?"
  - Rappeler qu'on peut prolonger si besoin

- [ ] **Monitoring usage**
  ```bash
  # Vérifier activité du trial user
  ssh ubuntu@watch.arkforge.fr
  cd /opt/arkwatch/api
  source venv/bin/activate

  python3 scripts/get_user_stats.py \
      --email prospect@company.com

  # Retourne : monitors créés, alertes configurées, dernière activité
  ```

- [ ] **Logger les interactions**
  - Mettre à jour conversion_tracker.csv : notes="interactions détaillées"

---

### Phase 7: Fin Trial → Conversion (J+13)

- [ ] **Envoyer email conversion J+13**
  - Utiliser Template 5 (Fin Trial)
  - Mentionner offre early bird (-50% pendant 3 mois)

- [ ] **Attendre confirmation du prospect**
  - Si "OUI" → Passer à Phase 8
  - Si "NON" → Logger dans conversion_tracker.csv : statut="trial_expired_no_conversion"
  - Si "PROLONGER" → Ajouter 7 jours de trial

- [ ] **Logger la décision**
  - Mettre à jour conversion_tracker.csv : conversion_decision="yes/no/extend"

---

### Phase 8: Génération Facture Stripe (5 min)

- [ ] **Confirmer tier choisi**
  - Starter (9€/mois) ?
  - Pro (29€/mois) ?
  - Business (99€/mois) ?

- [ ] **Générer facture Stripe Invoice**
  ```bash
  # Exécuter script génération facture
  cd /opt/claude-ceo/workspace/arkwatch/conversion

  python3 stripe_invoice_script.py \
      --email prospect@company.com \
      --tier pro \
      --send-email

  # Script crée facture Stripe + envoie email automatique
  ```

- [ ] **Vérifier envoi facture**
  - Checker dashboard Stripe : https://dashboard.stripe.com/invoices
  - Confirmer que l'email est bien parti

- [ ] **Logger la facture**
  - Mettre à jour conversion_tracker.csv : statut="invoice_sent"
  - Noter invoice_id Stripe

---

### Phase 9: Paiement & Activation (2 min)

- [ ] **Attendre paiement du prospect**
  - Stripe envoie webhook automatiquement
  - Backend active l'abonnement (status: active)

- [ ] **Vérifier activation**
  ```bash
  # Checker status abonnement
  ssh ubuntu@watch.arkforge.fr
  cd /opt/arkwatch/api
  source venv/bin/activate

  python3 scripts/get_user_subscription.py \
      --email prospect@company.com

  # Retourne : tier, status, customer_id, subscription_id
  ```

- [ ] **Envoyer email de bienvenue**
  - "Bienvenue parmi nos clients payants !"
  - Rappeler support disponible
  - Partager ressources avancées

- [ ] **Logger la conversion**
  - Mettre à jour conversion_tracker.csv : statut="converted_paid"
  - Noter date de paiement, montant, subscription_id

---

### Phase 10: Suivi Post-Conversion (J+30)

- [ ] **Check-in 1 mois après paiement**
  - Utiliser Template 6 (Post-Conversion)
  - Demander feedback
  - Proposer upsell si pertinent

- [ ] **Monitoring satisfaction**
  - Usage régulier ?
  - Alertes bien configurées ?
  - Pas de churn risk ?

- [ ] **Proposer parrainage**
  - Programme referral : 1 mois gratuit par parrainage
  - Fournir code promo personnalisé

- [ ] **Logger le suivi**
  - Mettre à jour conversion_tracker.csv : retention_status="active"

---

## 🎯 KPIs à Tracker

| Métrique | Objectif | Comment mesurer |
|----------|----------|-----------------|
| Temps de réponse lead | < 24h | Timestamp email - timestamp capture |
| Taux activation trial | > 50% | Trials créés / Leads contactés |
| Taux démo réalisée | > 30% | Demos / Trials actifs |
| Taux conversion trial→paid | > 20% | Paid / Trials terminés |
| Temps moyen conversion | < 21j | Date paiement - date première capture |

---

## ⚠️ Erreurs à Éviter

1. ❌ **Répondre trop tard** : > 24h = taux de conversion -50%
2. ❌ **Template générique** : Personnaliser selon source/contexte
3. ❌ **Négliger le support** : Répondre < 4h pendant trial
4. ❌ **Oublier de logger** : conversion_tracker.csv = source de vérité
5. ❌ **Pusher trop fort** : Soft sell > hard sell

---

## 📞 Contacts Utiles

- **Dashboard Stripe** : https://dashboard.stripe.com/
- **Dashboard ArkWatch** : https://watch.arkforge.fr/admin
- **Documentation API** : https://arkforge.fr/docs
- **Support technique** : Consulter CEO via task queue

---

*Checklist créée par Worker Fondations - Task #20260903*
