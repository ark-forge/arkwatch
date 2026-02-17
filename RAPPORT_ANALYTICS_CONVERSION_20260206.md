# RAPPORT ANALYTICS ARKWATCH - Analyse des blocages conversion
**Date**: 2026-02-06 22:10 UTC
**Auteur**: Worker Croissance
**Tâche**: #20260478
**Période analysée**: 2026-01-23 → 2026-02-06 (14 jours)

---

## 1. RÉSUMÉ EXÉCUTIF

| Métrique | Valeur | Verdict |
|----------|--------|---------|
| **Visiteurs humains réels sur arkwatch.html** | **1** | CRITIQUE |
| **Signups externes** | **0** | CRITIQUE |
| **Trafic tracking pixel** | 16 événements (tous internes/test) | N/A |
| **Taux de conversion landing→signup** | 0% (0/1) | N/A (échantillon insuffisant) |
| **Diagnostic principal** | **PROBLÈME D'ACQUISITION** | Le trafic = quasi 0 |

**Conclusion**: Le problème n'est PAS la conversion (page ou tunnel). Le problème est l'ACQUISITION. Personne ne visite la landing page. Il est impossible de diagnostiquer la conversion avec un échantillon de 1 visiteur humain.

---

## 2. DONNÉES DE TRAFIC DÉTAILLÉES

### 2.1 Trafic brut sur arkwatch.html (toutes sources confondues)

| Date | Visites totales | Humains réels | Bots/Crawlers | Interne (57.131.x) |
|------|-----------------|---------------|---------------|---------------------|
| 2026-02-04 | 8 | 1 (90.105.192.107) | 2 (MJ12bot, GPTBot) | 5 (curl tests) |
| 2026-02-06 | 143 | 1 (90.105.192.107) | 2 (YandexBot) | ~140 (curl/axios tests) |
| **TOTAL** | ~151 | **1 visiteur unique** | 4 | ~145 |

### 2.2 Identification du seul visiteur humain

- **IP**: 90.105.192.107
- **Device**: Windows 10 + Chrome 144 (Desktop) ET Android 10 + Chrome 144 (Mobile)
- **Comportement**: Visiteur récurrent depuis le 23/01, ~1866 requêtes historiques
- **Profil probable**: L'actionnaire lui-même (même IP sur dashboard depuis autonomix.arkforge.fr/login)
- **Ce n'est PAS un prospect externe**

### 2.3 Parcours du seul visiteur le 06/02

```
13:24:08 - GET / (homepage)
13:24:13 - GET /arkwatch.html (referrer: arkforge.fr/) → 200 OK
13:24:19 - GET /dashboard.html (referrer: arkwatch.html) → 200 OK
14:20:18 - GET /dashboard.html (retour direct)
14:22:11 - GET /api/v1/watches, /reports, /auth/account/data → API calls
14:26:54 - GET /api-docs.html
14:36:22 - GET /dashboard.html (retour)
14:36:37 - POST /api/v1/billing/portal → 400 ERROR
14:36:41 - POST /api/v1/billing/portal → 400 ERROR
14:36:43 - OPTIONS /api/v1/billing/checkout → 429 RATE LIMITED
14:36:44 - OPTIONS /api/v1/billing/checkout → 429 RATE LIMITED
16:19:41 - GET /dashboard.html (dernier accès)
```

**Observations critiques**:
- Le tunnel fonctionne (homepage → landing → dashboard)
- MAIS: billing/portal retourne 400 (2 fois) = **blocage paiement**
- PUIS: billing/checkout retourne 429 rate-limited = **impossible d'acheter**
- L'utilisateur abandonne après ces erreurs

### 2.4 Trafic global du serveur (hors interne)

| Métrique | Valeur |
|----------|--------|
| IPs externes uniques (06/02) | 161 |
| Dont crawlers/bots identifiés | ~140 (scanners, YandexBot, GPTBot, etc.) |
| Dont humains probables | ~5-10 (mais aucun sur arkwatch.html) |
| Requêtes suspectes | Nombreuses (.git/config, .env, wp-admin = scanners de vulnérabilités) |

### 2.5 Données du tracking pixel

Le tracking pixel (`/t.gif`) est **opérationnel mais ne reçoit aucun trafic externe**:

```
Total événements:     16 (tous de 57.131.27.61 = IP interne avec curl)
Pageviews arkwatch:   5  (tests internes)
CTA clicks:           2  (tests internes)
Signup attempts:      0  (externe)
Signup success:       0  (externe)
```

Le pixel tracking est **correctement configuré** mais n'a jamais été déclenché par un navigateur externe.

---

## 3. DIAGNOSTIC

### 3.1 Problème principal: ACQUISITION (pas conversion)

```
FUNNEL ACTUEL:

  Internet ──→ Landing ──→ Register ──→ Dashboard ──→ Payment

  ~0 visiteurs   1 visiteur   0 signup     0 paiement
  ▲               (actionnaire)
  │
  ICI EST LE PROBLÈME
  Aucun canal d'acquisition actif
```

**Il n'existe actuellement AUCUN canal d'acquisition actif qui amène du trafic vers arkwatch.html.**

### 3.2 Problèmes secondaires détectés (à résoudre APRÈS l'acquisition)

| # | Problème | Sévérité | Détail |
|---|----------|----------|--------|
| 1 | **Billing portal cassé** | HIGH | POST /billing/portal → 400 (2x). Le seul utilisateur actif n'a pas pu accéder au paiement |
| 2 | **Rate limiting trop agressif** | MEDIUM | billing/checkout → 429 après 2 tentatives. Bloque la conversion |
| 3 | **Tracking pixel non déclenché** | LOW | Le pixel ne fire pas depuis les navigateurs externes (possible: script bloqué ou non chargé correctement) |
| 4 | **Favicon 404** | LOW | /favicon.ico → 404 (mauvaise impression, signal amateur) |

### 3.3 Ce qui fonctionne

- Landing page charge rapidement (~34ms)
- Tunnel homepage → arkwatch → dashboard fonctionne
- API fonctionnelle (watches, reports, auth)
- Système de tracking correctement configuré côté serveur
- Pricing affiché avec 4 tiers
- Formulaire d'inscription présent

---

## 4. RECOMMANDATIONS D'ACTIONS (par priorité)

### PRIORITÉ 1 - ACQUISITION (sans trafic, rien d'autre ne compte)

| Action | Effort | Impact attendu | Délai |
|--------|--------|----------------|-------|
| **A. Publier sur Hacker News** (Show HN: ArkWatch) | 2h | 500-2000 visiteurs en 24h | Immédiat |
| **B. Publier sur Dev.to** (article technique) | 3h | 100-500 visiteurs | 1-2 jours |
| **C. Publier sur Reddit** (r/webdev, r/selfhosted, r/sideproject) | 1h | 200-1000 visiteurs | Immédiat |
| **D. Indexation Google** (soumettre sitemap, Search Console) | 1h | Trafic organique long terme | 2-4 semaines |
| **E. Product Hunt launch** | 4h | 500-3000 visiteurs | 1 jour |

### PRIORITÉ 2 - FIXER LES BLOCAGES CONVERSION (avant le lancement)

| Action | Effort | Impact |
|--------|--------|--------|
| **F. Fixer billing/portal (erreur 400)** | 2h | Critique - empêche tout paiement |
| **G. Ajuster rate limiting billing/checkout** | 30min | Empêche la conversion |
| **H. Ajouter favicon** | 5min | Signal de professionnalisme |

### PRIORITÉ 3 - AMÉLIORER LE SUIVI

| Action | Effort | Impact |
|--------|--------|--------|
| **I. Vérifier que le tracking JS fire en production** | 1h | Sans tracking, impossible de mesurer |
| **J. Ajouter Google Search Console** | 30min | Comprendre l'indexation |

---

## 5. PLAN D'ACTION RECOMMANDÉ

### Phase 1 - Préparation (avant tout lancement)
1. Fixer billing/portal et billing/checkout rate limit (actions F+G)
2. Ajouter favicon (action H)
3. Vérifier tracking pixel en condition réelle (action I)

### Phase 2 - Premier lancement
4. Publier sur Reddit r/selfhosted + r/webdev (action C - faible risque, bon feedback)
5. Publier article Dev.to (action B - SEO long terme)

### Phase 3 - Lancement principal
6. Show HN sur Hacker News (action A - gros volume potentiel)
7. Product Hunt (action E - après validation du tunnel)

---

## 6. MÉTRIQUES À SUIVRE POST-LANCEMENT

| Métrique | Cible J+7 | Cible J+30 |
|----------|-----------|------------|
| Visiteurs uniques arkwatch.html | > 100 | > 500 |
| Taux CTA click (landing→register) | > 10% | > 15% |
| Taux signup (register→compte créé) | > 30% | > 40% |
| Taux activation (signup→1er watch créé) | > 50% | > 60% |
| Taux conversion (free→paid) | > 2% | > 5% |

---

## 7. CONCLUSION

**Le diagnostic est clair: ArkWatch a un problème d'ACQUISITION, pas de conversion.**

Le produit est techniquement fonctionnel. Le tunnel de conversion fonctionne. La landing page est en place. Mais **aucun canal d'acquisition n'amène de trafic**. En 14 jours, un seul humain (probablement l'actionnaire) a visité arkwatch.html.

**Action immédiate requise**: Fixer les bugs billing (400/429), puis lancer une campagne d'acquisition multi-canal.

Sans trafic, toute optimisation de conversion est prématurée.
