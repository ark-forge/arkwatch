# ArkWatch - Onboarding Express 24h

> **Objectif** : Convertir un audit gratuit en client payant avec monitoring actif en **moins de 24 heures**.

---

## Vue d'ensemble du processus

```
AUDIT GRATUIT              APPEL DÉCOUVERTE          ACTIVATION CLIENT
  [H+0]                      [H+2 à H+6]               [H+6 à H+24]

  Soumission form    →    Appel 30min + démo live  →  Setup monitoring Pro
  Confirmation email       Proposition commerciale     Premiers checks actifs
  Pré-analyse infra        Signature/paiement          Dashboard partagé
```

**KPIs cibles** :
- Délai confirmation audit → appel : < 6h
- Délai appel → proposition envoyée : < 1h
- Délai signature → monitoring actif : < 2h
- Délai total audit → client payant : < 24h

---

## PHASE 1 : Confirmation Audit (H+0 → H+2)

### 1.1 Email de confirmation immédiat (automatique)

**Déclenché par** : `POST /api/audit-gratuit/submit`

**Objet** : `Votre audit monitoring ArkWatch — créneau réservé`

```
Bonjour {prénom},

Merci pour votre demande d'audit monitoring gratuit !

📋 RÉCAPITULATIF
- Site audité : {website_url}
- Stack actuelle : {monitoring_stack}
- Problème signalé : {pain_point}

📅 VOTRE CRÉNEAU
Nous vous proposons un appel de 30 minutes pour vous présenter
les résultats de l'audit en live :

  → Date proposée : {demain ou surlendemain}
  → Créneaux disponibles : 9h, 11h, 14h, 16h (CET)

👉 Répondez à cet email avec votre créneau préféré,
   ou proposez le vôtre.

En attendant, nous commençons déjà l'analyse de {website_url}.

Cordialement,
L'équipe ArkWatch
https://watch.arkforge.fr
```

### 1.2 Notification interne (automatique)

Email envoyé à `apps.desiorac@gmail.com` avec :
- Coordonnées du lead
- Stack actuelle (pour préparer l'audit)
- Pain point (pour personnaliser l'appel)
- Lien direct vers le profil lead dans le tracking

### 1.3 Pré-analyse automatique (background)

Lancer immédiatement via API :
```bash
curl -X POST https://watch.arkforge.fr/api/v1/quick-check \
  -H "Content-Type: application/json" \
  -d '{"url": "{website_url}", "checks": ["uptime", "ssl", "response_time", "headers"]}'
```

Résultats stockés pour l'appel — permet de montrer des données réelles dès le premier contact.

---

## PHASE 2 : Préparation appel (H+2 → H+6)

### 2.1 Checklist pré-appel (à valider AVANT l'appel)

#### Informations lead
- [ ] Nom et prénom confirmés
- [ ] Email vérifié (réponse reçue)
- [ ] Créneau appel confirmé
- [ ] Site web accessible (pas de blocage IP/geo)
- [ ] Stack monitoring actuelle identifiée

#### Analyse technique préliminaire
- [ ] Quick-check exécuté (uptime, SSL, response time)
- [ ] Certificat SSL : date expiration notée
- [ ] Temps de réponse moyen mesuré (baseline)
- [ ] Headers sécurité analysés (HSTS, CSP, X-Frame)
- [ ] Pages critiques identifiées (/, /login, /api, /checkout si e-commerce)

#### Préparation démo
- [ ] Compte démo ArkWatch prêt (ou sandbox)
- [ ] 3 endpoints du client pré-configurés dans le dashboard
- [ ] Alertes email configurées vers une adresse test
- [ ] Scénario de panne simulée prêt (pour montrer le temps d'alerte 30s)

#### Préparation commerciale
- [ ] Pricing page ouverte : https://watch.arkforge.fr/pricing.html
- [ ] Estimation du plan adapté (Free vs Pro) selon nombre d'endpoints
- [ ] Calcul ROI personnalisé prêt (coût downtime vs €29/mois)
- [ ] Lien Stripe checkout prêt pour paiement immédiat

### 2.2 Template rapport d'audit

Préparer un mini-rapport (1 page) avec les résultats du quick-check :

```markdown
# Rapport Audit Express — {company_name}

**Date** : {date}
**Site audité** : {website_url}
**Analyste** : ArkWatch Team

## Résultats

| Métrique              | Valeur          | Statut   |
|-----------------------|-----------------|----------|
| Uptime (24h)          | {uptime}%       | ✅/⚠️/❌ |
| Temps réponse moyen   | {response_ms}ms | ✅/⚠️/❌ |
| Certificat SSL        | Expire {date}   | ✅/⚠️/❌ |
| Headers sécurité      | {score}/5       | ✅/⚠️/❌ |

## Risques identifiés
1. {risque_1}
2. {risque_2}
3. {risque_3}

## Recommandation
Monitoring continu avec alertes temps réel (30s) sur {n} endpoints critiques.
→ Plan Pro ArkWatch : €29/mois (offre early adopter, normalement €49/mois)
```

---

## PHASE 3 : Appel découverte + proposition (H+6)

### 3.1 Script d'appel (30 minutes)

**[0-5 min] Introduction**
- "Merci d'avoir demandé l'audit. On a déjà analysé votre site."
- Confirmer le pain point mentionné dans le formulaire
- "Laissez-moi vous montrer ce qu'on a trouvé."

**[5-15 min] Présentation résultats audit**
- Partager écran → mini-rapport d'audit
- Montrer les métriques réelles (temps de réponse, SSL, headers)
- Identifier 2-3 risques concrets et chiffrables
- "Si votre site tombe pendant 2h un vendredi soir, combien ça coûte ?"

**[15-22 min] Démo live ArkWatch**
- Montrer le dashboard avec les endpoints du client déjà configurés
- Simuler une alerte → montrer le délai de 30 secondes
- Montrer les résumés IA des changements détectés
- "En 60 secondes, vos 10 endpoints les plus critiques sont surveillés."

**[22-27 min] Proposition commerciale**
- "On a une offre early adopter à €29/mois au lieu de €49."
- Montrer la pricing page
- Calcul ROI : "1h de downtime évité = X mois d'abonnement payés"
- "On peut activer votre monitoring dans les 2 prochaines heures."

**[27-30 min] Closing**
- Si OUI → "Je vous envoie le lien de paiement, on active immédiatement."
- Si HÉSITATION → "On propose 14 jours gratuits, sans carte bancaire."
- Si NON → "Je vous envoie le rapport complet. N'hésitez pas à revenir."

### 3.2 Email post-appel (envoi immédiat après l'appel)

**Si intéressé / accepte** :

**Objet** : `ArkWatch Pro — Activation monitoring {company_name}`

```
Bonjour {prénom},

Suite à notre échange, voici le récapitulatif :

📊 RÉSULTATS AUDIT
{résumé 3 points clés}

🚀 PROCHAINES ÉTAPES
1. Finaliser le paiement : {lien_stripe_checkout}
   → €29/mois (tarif early adopter verrouillé)
2. Nous transmettre la liste de vos endpoints (voir checklist ci-dessous)
3. Activation monitoring sous 2h après réception

📋 CHECKLIST ENDPOINTS (à nous retourner)
- URL endpoint 1 : ___
- URL endpoint 2 : ___
- URL endpoint 3 : ___
- (ajoutez autant que nécessaire)
- Email pour les alertes : ___
- Fréquence souhaitée : ☐ 5min ☐ 15min ☐ 1h

💡 RAPPEL : Votre tarif early adopter (€29/mois au lieu de €49)
   est garanti à vie tant que votre abonnement reste actif.

Cordialement,
L'équipe ArkWatch
```

**Si hésitant** :

**Objet** : `Votre rapport d'audit ArkWatch + essai gratuit 14 jours`

```
Bonjour {prénom},

Merci pour notre échange. Voici votre rapport d'audit complet en pièce jointe.

🎁 OFFRE SPÉCIALE
Testez ArkWatch Pro gratuitement pendant 14 jours :
→ {lien_trial_14d}
- Pas de carte bancaire requise
- Monitoring illimité pendant 14 jours
- Alertes en 30 secondes

Le rapport montre {risque_principal} — avec ArkWatch, vous seriez
alerté en 30 secondes au lieu de le découvrir par vos utilisateurs.

N'hésitez pas à répondre à cet email si vous avez des questions.

Cordialement,
L'équipe ArkWatch
```

---

## PHASE 4 : Activation client (H+6 → H+24)

### 4.1 Checklist activation technique

**Pré-requis reçus du client** :
- [ ] Paiement confirmé (Stripe webhook `checkout.session.completed`)
- [ ] Liste des endpoints à monitorer
- [ ] Email(s) pour les alertes
- [ ] Fréquence de check souhaitée

**Configuration ArkWatch** :
- [ ] Compte Pro créé (email client + API key générée)
- [ ] Endpoints configurés dans le système de monitoring
- [ ] Alertes email activées
- [ ] Alertes SMS activées (si numéro fourni)
- [ ] Premier check exécuté avec succès
- [ ] Dashboard accessible et données visibles

**Vérification** :
- [ ] Tous les endpoints répondent (pas de faux positifs)
- [ ] Alerte test envoyée et reçue par le client
- [ ] Temps de réponse baseline enregistré
- [ ] SSL monitoring activé si HTTPS

### 4.2 Email d'activation (envoi dès que monitoring actif)

**Objet** : `✅ ArkWatch actif — {n} endpoints surveillés pour {company_name}`

```
Bonjour {prénom},

Votre monitoring ArkWatch Pro est maintenant actif !

📊 VOTRE CONFIGURATION
- Endpoints surveillés : {n}
- Fréquence de check : toutes les {interval} minutes
- Alertes email : {email}
- Alertes SMS : {phone ou "non configuré"}

🔗 ACCÈS DASHBOARD
→ https://watch.arkforge.fr/dashboard
   Login : {email}
   API Key : {api_key_masked}

📱 CE QUI SE PASSE MAINTENANT
- Vos endpoints sont vérifiés toutes les {interval} minutes
- En cas de panne : alerte en 30 secondes par email (+ SMS si configuré)
- Résumé IA quotidien des changements détectés
- Dashboard temps réel accessible 24/7

📞 SUPPORT
Répondez à cet email pour toute question.
Support prioritaire inclus dans votre plan Pro.

Bienvenue chez ArkWatch !
L'équipe ArkWatch
```

### 4.3 Suivi J+1 (automatique, 24h après activation)

**Objet** : `Vos premières 24h de monitoring — {company_name}`

```
Bonjour {prénom},

Voici le résumé de vos premières 24 heures de monitoring :

📊 BILAN 24H
- Uptime : {uptime}%
- Checks effectués : {total_checks}
- Temps réponse moyen : {avg_ms}ms
- Incidents détectés : {incidents}
- Alertes envoyées : {alerts}

{si incidents > 0}
⚠️ INCIDENTS DÉTECTÉS
{liste des incidents avec timestamps}
→ Sans ArkWatch, ces incidents seraient passés inaperçus.
{/si}

{si incidents == 0}
✅ AUCUN INCIDENT
Tout fonctionne parfaitement. ArkWatch veille.
{/si}

Des questions ? Répondez à cet email.

L'équipe ArkWatch
```

---

## Récapitulatif timeline

| Étape | Délai | Action | Responsable |
|-------|-------|--------|-------------|
| H+0 | Immédiat | Email confirmation audit + pré-analyse | Automatique |
| H+0→H+2 | 2h | Quick-check technique + préparation démo | Fondations |
| H+2→H+6 | 4h max | Appel découverte 30min | Actionnaire/CEO |
| H+6 | Post-appel | Email proposition ou trial | Actionnaire/CEO |
| H+6→H+8 | 2h | Réception paiement + endpoints client | Client |
| H+8→H+10 | 2h | Configuration monitoring + activation | Fondations |
| H+10 | Immédiat | Email activation "monitoring actif" | Automatique |
| H+24 | J+1 | Email bilan premières 24h | Automatique |

---

## Ressources et liens

| Ressource | URL / Chemin |
|-----------|-------------|
| Pricing page | https://watch.arkforge.fr/pricing.html |
| Trial 14j | https://watch.arkforge.fr/trial-14d.html |
| Démo interactive | https://watch.arkforge.fr/demo.html |
| Audit gratuit | https://watch.arkforge.fr/audit-gratuit-monitoring.html |
| API Quick-check | `POST /api/v1/quick-check` |
| API Trial signup | `POST /api/trial-14d/signup` |
| Audit submit | `POST /api/audit-gratuit/submit` |
| Stripe checkout | Via `/api/mcp-checkout` |

---

## Objection handling

| Objection | Réponse |
|-----------|---------|
| "C'est trop cher" | "€29/mois = le coût de 15 minutes de downtime. Combien coûte 1h de panne pour vous ?" |
| "On a déjà du monitoring" | "ArkWatch complète votre stack. Alertes en 30s vs minutes avec {leur outil}. Et résumés IA inclus." |
| "Je dois en parler à mon équipe" | "Bien sûr. En attendant, activez l'essai 14 jours gratuit — votre équipe verra les résultats directement." |
| "On n'a pas le budget" | "Plan gratuit disponible pour 3 URLs. Commencez par là, upgradez quand vous voyez la valeur." |
| "C'est quoi la différence avec Datadog/New Relic ?" | "10x moins cher, setup en 60s, pas besoin d'agent. Monitoring externe pur, complémentaire à l'APM interne." |
| "RGPD ?" | "Infrastructure 100% EU, conforme RGPD. Pas de transfert US." |

---

*Document créé le 2026-02-10 — ArkWatch Onboarding Express v1.0*
