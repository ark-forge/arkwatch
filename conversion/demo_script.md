# Script Démo 1-to-1 ArkWatch

**Créé**: 2026-02-09
**Usage**: Guide pour réaliser une démo personnalisée Zoom de 15-30 min
**Objectif**: Maximiser activation trial + répondre aux objections

---

## 🎯 Objectifs de la Démo

1. **Montrer la valeur** : ArkWatch fait gagner du temps sur la veille manuelle
2. **Activer le trial** : Prospect crée son premier monitor pendant la démo
3. **Identifier blocages** : Comprendre les objections et y répondre
4. **Qualifier le besoin** : Confirmer le fit product-market
5. **Planifier le suivi** : Check-in J+7 et conversion J+13

---

## ⏱️ Structure de la Démo (30 min)

| Timing | Phase | Contenu |
|--------|-------|---------|
| 0-2 min | Intro | Présentations + contexte prospect |
| 2-5 min | Discovery | Questions sur cas d'usage |
| 5-15 min | Démo live | Création monitor + alertes |
| 15-25 min | Q&A | Réponses aux questions |
| 25-30 min | Next steps | Plan d'action + suivi |

---

## 📋 Script Étape par Étape

### Phase 1: Introduction (0-2 min)

**Vous** :
> "Bonjour [Prénom], merci d'avoir pris ce créneau ! Je suis [Votre nom] d'ArkForge, créateur d'ArkWatch.
>
> Avant de commencer, j'ai vu que vous vous êtes inscrit via [source : demo page / pricing / LinkedIn]. Pouvez-vous me dire en 2 mots ce qui vous a attiré chez ArkWatch ?"

**Objectif** : Laisser le prospect parler en premier, comprendre son contexte.

**Notes** : Écouter activement, noter les mots-clés (concurrents, tarification, veille réglementaire, etc.)

---

### Phase 2: Discovery Questions (2-5 min)

**Vous** :
> "Super, merci pour le contexte. J'ai quelques questions rapides pour adapter la démo à votre cas d'usage :
>
> 1. **Quels sites souhaitez-vous surveiller ?**
>    - Concurrents directs ?
>    - Fournisseurs (tarifs, disponibilité) ?
>    - Veille réglementaire (légal, compliance) ?
>    - Autre chose ?
>
> 2. **À quelle fréquence faites-vous cette veille aujourd'hui ?**
>    - Quotidienne ? Hebdomadaire ? Mensuelle ?
>    - Combien de temps ça vous prend par semaine ?
>
> 3. **Que se passe-t-il si vous ratez un changement important ?**
>    - Perte de compétitivité ?
>    - Risque de non-conformité ?
>    - Opportunité manquée ?

**Objectif** : Qualifier le pain point et l'urgence. Identifier le ROI.

**Notes** : Adapter la démo selon les réponses (focus sur les use cases pertinents).

---

### Phase 3: Démo Live (5-15 min)

#### 3.1 Partage d'écran (votre côté)

**Vous** :
> "Parfait, je vais vous montrer comment ArkWatch fonctionne en créant un monitor en temps réel. Je partage mon écran."

**Actions** :
1. Ouvrir https://watch.arkforge.fr/dashboard
2. Se connecter avec votre compte démo (ou compte prospect si déjà créé)
3. Montrer le dashboard vide (si nouveau compte)

---

#### 3.2 Création d'un Monitor (3 min)

**Vous** :
> "Imaginez que vous voulez surveiller la page de tarification d'un concurrent. Voici comment faire en 30 secondes :
>
> 1. Je clique sur 'Créer un monitor'
> 2. Je colle l'URL du site concurrent (ex: https://competitor.com/pricing)
> 3. Je donne un nom descriptif : 'Concurrent X - Pricing'
> 4. Je choisis la fréquence de vérification : toutes les 6 heures
> 5. Je clique sur 'Créer'
>
> Et voilà ! ArkWatch va maintenant vérifier cette page toutes les 6 heures et me notifier si quelque chose change."

**Montrer** :
- Simplicité de l'interface (UX)
- Rapidité de création (< 30 sec)
- Aperçu du site surveillé (screenshot)

---

#### 3.3 Configuration des Alertes (4 min)

**Vous** :
> "Maintenant, configurons les alertes pour être notifié en temps réel :
>
> 1. Je clique sur le monitor créé
> 2. Section 'Alertes' → 'Ajouter une alerte'
> 3. Je choisis le type : Email (ou Slack, webhook)
> 4. Je configure les triggers :
>    - Tout changement (le plus simple)
>    - Ou changement dans une zone spécifique (avancé)
> 5. Je configure la fréquence : Immédiat (ou quotidien, hebdomadaire)
> 6. J'ajoute mon email
> 7. Je sauvegarde
>
> Dès qu'ArkWatch détecte un changement sur cette page, je reçois un email avec :
> - Un résumé du changement (généré par IA)
> - Un diff visuel (avant/après)
> - Un lien vers la page pour vérifier

**Montrer** :
- Flexibilité des alertes (email, Slack, webhook)
- Puissance de l'IA (résumé intelligent)
- Gain de temps (pas besoin de visiter le site manuellement)

---

#### 3.4 Démonstration d'un Changement Détecté (4 min)

**Option A : Si changement récent disponible**

**Vous** :
> "Laissez-moi vous montrer un exemple réel de changement détecté hier sur un autre monitor."

**Actions** :
1. Ouvrir l'historique d'un monitor existant
2. Montrer l'email reçu (screenshot ou email réel)
3. Montrer le diff visuel (avant/après)
4. Expliquer le résumé IA : "Le prix du plan Pro est passé de 29€ à 39€"

**Option B : Si pas de changement disponible (créer un faux changement en staging)**

**Vous** :
> "Pour simuler un changement, je vais utiliser notre environnement de test."

**Actions** :
1. Montrer un monitor sur une page de test
2. Déclencher un changement artificiellement (modifier la page de test)
3. Rafraîchir le dashboard ArkWatch
4. Montrer l'alerte générée en temps réel

---

#### 3.5 Cas d'Usage Avancés (2 min, optionnel)

**Vous** :
> "ArkWatch peut faire bien plus que surveiller des tarifs. Voici quelques exemples :
>
> - **Veille concurrentielle** : Détecter nouvelles features, blog posts, offres d'emploi
> - **Monitoring fournisseurs** : Disponibilité produits, changements de stock
> - **Compliance** : Mises à jour légales, CGV, politique de confidentialité
> - **SEO** : Changements de méta-descriptions, title tags
> - **E-commerce** : Prix, promotions, disponibilité
>
> Lequel de ces cas vous intéresse le plus ?"

**Objectif** : Élargir la vision du prospect, identifier d'autres use cases.

---

### Phase 4: Questions & Objections (15-25 min)

**Vous** :
> "Super, vous avez vu l'essentiel. Avez-vous des questions ?"

#### Questions Fréquentes & Réponses

**Q1: "Quelle est la précision de la détection ?"**

**R** :
> "ArkWatch détecte tout changement textuel ou visuel. L'IA filtre les changements insignifiants (dates, heures, compteurs) pour ne notifier que les changements importants. Taux de faux positifs < 5%."

---

**Q2: "Peut-on surveiller des sites avec login ?"**

**R** :
> "Oui, avec la fonctionnalité 'Authenticated monitoring'. Vous fournissez des credentials (stockés de manière sécurisée), et ArkWatch se connecte pour surveiller les pages protégées. Disponible en plan Pro et Business."

---

**Q3: "Quelle est la fréquence de vérification ?"**

**R** :
> "Ça dépend de votre plan :
> - **Starter** : Toutes les 24h
> - **Pro** : Toutes les 1h-6h (configurable)
> - **Business** : Jusqu'à toutes les 15 minutes
>
> Pour la plupart des cas d'usage (tarifs concurrents, blog posts), 6h est largement suffisant."

---

**Q4: "Comment gérez-vous les sites dynamiques (JS, React, etc.) ?"**

**R** :
> "ArkWatch utilise un navigateur headless (Playwright) qui exécute le JavaScript et capture le DOM final. On surveille ce que l'utilisateur voit réellement, pas le code source HTML brut."

---

**Q5: "Et si un site bloque les scrapers ?"**

**R** :
> "On utilise des techniques anti-détection (rotation d'IP, user-agents réalistes, délais aléatoires). Taux de succès > 95%. Pour les sites très protégés (Cloudflare strict), on propose des proxies résidentiels (option payante)."

---

**Q6: "Quelle est la différence avec des outils comme Visualping ou ChangeTower ?"**

**R** :
> "Les principales différences :
> 1. **Prix** : ArkWatch est 2-3x moins cher (29€ vs 79€ pour des features équivalentes)
> 2. **IA** : Résumés intelligents des changements (pas juste un diff brut)
> 3. **Flexibilité** : API REST complète pour intégrations custom
> 4. **Support** : Réponse < 4h par email, démo 1-to-1 incluse
> 5. **Trial** : 14 jours sans CB (vs 7j avec CB chez concurrents)

---

**Q7: "Combien de monitors peut-on créer ?"**

**R** :
> "Ça dépend du plan :
> - **Free** : 1 monitor
> - **Starter (9€)** : 10 monitors
> - **Pro (29€)** : 100 monitors
> - **Business (99€)** : 500 monitors
>
> Pour la plupart des PME, le plan Pro suffit largement."

---

**Q8: "Peut-on exporter les données ?"**

**R** :
> "Oui, via l'API REST. Vous pouvez récupérer :
> - Historique complet des changements (JSON, CSV)
> - Diffs visuels (images PNG)
> - Métadonnées (timestamps, checksums)
>
> Intégrations possibles avec Zapier, Make, n8n, etc."

---

### Phase 5: Next Steps & Closing (25-30 min)

**Vous** :
> "Parfait, merci pour vos questions ! Voici ce que je vous propose pour la suite :
>
> 1. **Aujourd'hui** : Je vous envoie vos credentials par email (API key + dashboard)
> 2. **Cette semaine** : Vous créez vos premiers monitors (je suis dispo pour aider)
> 3. **J+7** : Je vous envoie un check-in rapide pour voir comment ça se passe
> 4. **J+13** : Discussion sur la conversion vers un plan payant (si ça vous convient)
>
> Des questions ? Hésitations ? C'est le moment d'en parler."

**Objectif** : Clarifier les attentes, rassurer sur le support, créer un engagement.

---

**Vous** :
> "Dernière chose : Si vous êtes satisfait après le trial, je vous offre **-50% pendant 3 mois** en tant qu'early adopter. Ça vous intéresse ?"

**Objectif** : Créer un incentive pour conversion rapide.

---

**Vous** :
> "Super, merci [Prénom] pour votre temps ! Je vous envoie un recap par email dans 5 minutes avec :
> - Lien dashboard
> - Credentials
> - Documentation
> - Mon contact direct
>
> N'hésitez pas à m'écrire si vous avez la moindre question. Je réponds sous 4h max.
>
> Bon trial et à très bientôt !"

---

## 📊 Post-Démo Actions

Immédiatement après la démo :

1. **Envoyer email de recap** (template ci-dessous)
2. **Logger la démo** dans `conversion_tracker.csv` : demo_done="yes"
3. **Ajouter notes** dans conversion_tracker : impressions, objections, fit
4. **Planifier suivi** : Check-in J+3 et J+7

---

## 📧 Email Template Post-Démo

**Subject** : `Recap démo ArkWatch + vos accès 🚀`

**Body** :
```
Bonjour [Prénom],

Merci pour la démo de tout à l'heure ! C'était un plaisir d'échanger avec vous.

Voici un recap de ce qu'on a vu :
✅ Création d'un monitor en 30 secondes
✅ Configuration des alertes email
✅ Détection de changements en temps réel
✅ [Autre point spécifique discuté]

🔑 **Vos accès ArkWatch** :
- Dashboard : https://watch.arkforge.fr/dashboard
- API Key : ak_live_ABC123XYZ456
- Trial valable jusqu'au : [Date]
- Documentation : https://arkforge.fr/docs

🎯 **Quick Start** :
1. Connectez-vous avec votre API key
2. Créez votre premier monitor sur [site mentionné pendant démo]
3. Configurez une alerte email
4. Testez la détection !

📞 **Support direct** :
Si vous avez la moindre question, répondez simplement à cet email. Je réponds sous 4h max.

🎁 **Offre early bird** :
Si vous convertissez en plan payant après le trial, je vous offre **-50% pendant 3 mois** (14.50€/mois au lieu de 29€ pour le plan Pro).

Je vous envoie un check-in rapide dans 3 jours pour voir comment ça se passe.

Bon trial !

Cordialement,
[Votre nom]
ArkWatch by ArkForge
https://arkforge.fr
```

---

## 🎯 KPIs Démo

| Métrique | Objectif |
|----------|----------|
| Taux d'acceptation démo | > 30% des trials |
| Durée moyenne démo | 20-30 min |
| Questions posées | > 3 (signe d'engagement) |
| Activation post-démo (J+1) | > 80% |
| Conversion trial→paid (avec démo) | > 40% |
| NPS post-démo | > 8/10 |

---

## ⚠️ Erreurs à Éviter

1. ❌ **Trop parler** : Laisser le prospect parler 50% du temps
2. ❌ **Trop technique** : Focus sur la valeur, pas les features
3. ❌ **Ignorer les objections** : Adresser chaque objection sérieusement
4. ❌ **Aller trop vite** : Adapter le rythme au prospect
5. ❌ **Oublier le suivi** : Toujours confirmer les next steps

---

## 🔄 Amélioration Continue

Après chaque démo :
- Noter les questions fréquentes
- Identifier les objections récurrentes
- Mesurer le taux de conversion démo→trial→paid
- Itérer sur le script selon les retours

---

*Script créé par Worker Fondations - Task #20260903*
