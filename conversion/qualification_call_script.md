# Script Appel Qualificatif - ArkWatch (7 minutes)

**Objectif**: Qualifier le lead, identifier le pain, closer en trial ou abo direct.
**Cible**: Top 5 leads HOT (audit gratuit complété, email ouvert, >2min sur page)

---

## PRE-APPEL (30s de préparation)

Avant d'appeler, vérifier dans les données:
- [ ] Nom et email du lead
- [ ] Stack déclaré (si audit gratuit rempli)
- [ ] URL monitoré (si fourni)
- [ ] Temps passé sur la page / scroll depth
- [ ] Emails ouverts (tracking pixel)
- [ ] Source (Dev.to, LinkedIn, direct, etc.)

---

## PHASE 1 — ACCROCHE (45s)

> **"Bonjour [Prénom], c'est [Votre nom] d'ArkForge.**
>
> **Vous avez [complété notre audit gratuit / visité notre page monitoring] récemment. Je voulais vous contacter directement pour comprendre vos besoins et voir si on peut vous aider.**
>
> **Vous avez 7 minutes ?"**

Si NON → **"Pas de souci, quand est-ce qu'on pourrait se rappeler ? Je vous envoie un lien Calendly."**
Si OUI → continuer

---

## PHASE 2 — PAIN DISCOVERY (2min)

Poser ces 3 questions dans l'ordre:

### Question 1: Situation actuelle
> **"Aujourd'hui, comment est-ce que votre équipe détecte les pannes ou les dégradations de performance ?"**

_Écouter: Outils utilisés (Datadog, Pingdom, rien ?), process, qui est alerté._

### Question 2: Impact business
> **"La dernière fois qu'un incident n'a pas été détecté à temps, qu'est-ce qui s'est passé côté business ?"**

_Écouter: Perte clients, SLA cassé, incident post-mortem, stress on-call._

### Question 3: Objectif
> **"Si vous pouviez améliorer une seule chose dans votre monitoring, ce serait quoi ?"**

_Écouter: Couverture, vitesse détection, faux positifs, coût outil actuel._

---

## PHASE 3 — SOLUTION MAPPING (2min)

Adapter selon les réponses:

### Si pas d'outil actuellement:
> **"Ce que nos clients dans votre situation ont fait: ils ont commencé avec ArkWatch en 10 minutes — 10 endpoints monitorés, checks toutes les 5 min, alertes email + IA qui résume chaque incident.**
>
> **Le setup prend littéralement 2 minutes. Vous collez vos URLs et c'est parti."**

### Si outil existant trop cher / complexe:
> **"On a beaucoup de clients qui viennent de [Datadog/Pingdom/New Relic] parce que le pricing est devenu prohibitif. ArkWatch démarre à 9€/mois pour un monitoring complet, et l'IA fait le travail de triage que votre équipe fait manuellement."**

### Si problème de couverture:
> **"ArkWatch surveille vos endpoints toutes les 5 minutes depuis 3 régions. L'IA détecte les changements subtils — pas juste les 500 errors, mais aussi les dégradations de contenu, les certificats SSL, les changements de structure."**

### Toujours ajouter:
> **"Et le plus important: quand il y a un incident, vous recevez un résumé IA qui vous dit exactement ce qui a changé et quoi faire. Pas de dashboard à scruter pendant 30 minutes."**

---

## PHASE 4 — PRICING + CLOSE (1min30)

### Présentation offre:
> **"On a 3 formules:**
>
> - **Starter à 9€/mois** — 10 monitors, checks 5min, alertes IA
> - **Pro à 29€/mois** — illimité, SMS, API complète, rapports automatisés
> - **Business à 99€/mois** — dédié, SLA, support prioritaire
>
> **Toutes les formules incluent 14 jours d'essai gratuit, sans carte bancaire."**

### Tentative de close:
> **"Vu ce que vous m'avez décrit, je pense que le [Starter/Pro] serait parfait pour commencer. Est-ce qu'on lance votre essai gratuit maintenant ? Je vous envoie le lien par email, c'est fait en 2 minutes."**

### Si hésitation:
> **"Aucun engagement. 14 jours gratuits, vous testez avec vos vrais endpoints, et si ça ne convient pas, vous ne payez rien. Le pire qui puisse arriver c'est que vous découvrez un problème sur votre infra pendant l'essai."**

---

## PHASE 5 — NEXT STEPS (30s)

### Si OUI (close):
> **"Parfait ! Je vous envoie le lien d'essai maintenant. Vous recevrez un email de bienvenue avec votre clé API et un guide de démarrage en 3 étapes. Si vous avez la moindre question, répondez directement à l'email."**

Action: Envoyer lien trial-14d.html par email immédiatement après l'appel.

### Si "je réfléchis":
> **"Bien sûr. Je vous envoie un récap par email avec les 3 formules et le lien d'essai gratuit. N'hésitez pas à répondre si vous avez des questions. On est très réactifs."**

Action: Envoyer email récap avec lien trial + booking 15min follow-up.

### Si NON:
> **"Pas de souci. Si jamais le sujet revient sur la table, vous avez mon email. Bonne continuation !"**

---

## OBJECTIONS FRÉQUENTES

| Objection | Réponse |
|-----------|---------|
| "C'est trop cher" | "9€/mois c'est le prix d'un café par semaine. Combien coûte 1h de downtime non détecté ?" |
| "On utilise déjà X" | "Est-ce que X vous alerte en 30 secondes ? Est-ce que X vous dit quoi faire après l'alerte ?" |
| "Pas le temps" | "Le setup prend 2 minutes. Collez 3 URLs et l'IA fait le reste." |
| "Je dois en parler à mon CTO" | "Je comprends. Je vous envoie un one-pager technique qu'il peut lire en 2min. On peut faire un call à 3 si besoin." |
| "On n'a pas de budget" | "14 jours gratuits sans CB. Si ça apporte de la valeur, le budget se justifie tout seul." |

---

## MÉTRIQUES DE SUCCÈS

| Métrique | Objectif |
|----------|----------|
| Taux de réponse (décroche) | > 30% |
| Taux qualification (pain identifié) | > 60% |
| Taux conversion appel → trial | > 25% |
| Taux conversion appel → abo direct | > 5% |
| Durée moyenne appel | 5-8 min |

---

## DONNÉES LEAD À REMPLIR APRÈS L'APPEL

```json
{
  "lead_email": "",
  "date_appel": "",
  "duree_min": 0,
  "pain_identifie": "",
  "outil_actuel": "",
  "budget_mentionne": false,
  "decision_maker": true,
  "resultat": "trial|abo|reflexion|non",
  "next_action": "",
  "notes": ""
}
```

---

## TOP 5 HOT LEADS — CRITÈRES DE SÉLECTION

Prioriser les leads par heat score (source: unified_email_tracking.json):

1. **Score > 80**: Email ouvert + click + formulaire commencé → APPELER EN PREMIER
2. **Score 60-80**: Email ouvert + temps > 3min sur page → Appeler
3. **Score 40-60**: Audit gratuit soumis → Appeler dans les 24h
4. **Score < 40**: Simple visite → Email nurturing seulement

Commande pour extraire les top 5:
```bash
python3 -c "
import json
from pathlib import Path

# Load unified tracking
tracking = json.load(open('/opt/claude-ceo/workspace/arkwatch/data/unified_email_tracking.json'))
leads = tracking.get('leads', {})

# Sort by heat score
ranked = sorted(leads.items(), key=lambda x: x[1].get('heat_score', 0), reverse=True)

print('TOP 5 HOT LEADS:')
for i, (lid, data) in enumerate(ranked[:5], 1):
    print(f'{i}. {data.get(\"email\", \"N/A\")} — Score: {data.get(\"heat_score\", 0)} — Opens: {data.get(\"opens\", 0)} — Clicks: {data.get(\"clicks\", 0)}')
"
```
