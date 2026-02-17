# Guide UTM - Équipe Marketing ArkWatch

## 🎯 Objectif

Ce guide vous aide à créer des liens trackés pour mesurer la performance de chaque canal marketing.

## 📊 Principe

Ajoutez `?ref=CANAL` à vos liens vers ArkWatch. Cela permet de savoir d'où viennent vos signups.

## 🔗 Liens prêts à utiliser

### Landing page principale

**URL de base** : `https://arkforge.fr/arkwatch.html`

### Réseaux sociaux

| Plateforme | Lien à utiliser |
|------------|-----------------|
| Twitter | `https://arkforge.fr/arkwatch.html?ref=twitter` |
| LinkedIn | `https://arkforge.fr/arkwatch.html?ref=linkedin` |
| Reddit | `https://arkforge.fr/arkwatch.html?ref=reddit` |
| Hacker News | `https://arkforge.fr/arkwatch.html?ref=hackernews` |
| Product Hunt | `https://arkforge.fr/arkwatch.html?ref=producthunt` |

### Communautés tech

| Communauté | Lien à utiliser |
|------------|-----------------|
| Dev.to | `https://arkforge.fr/arkwatch.html?ref=devto` |
| Hashnode | `https://arkforge.fr/arkwatch.html?ref=hashnode` |
| IndieHackers | `https://arkforge.fr/arkwatch.html?ref=indiehackers` |

### Campagnes spécifiques

| Campagne | Lien à utiliser | Quand l'utiliser |
|----------|-----------------|------------------|
| Email outreach | `https://arkforge.fr/arkwatch.html?ref=outreach` | Emails de prospection |
| Newsletter | `https://arkforge.fr/arkwatch.html?ref=newsletter` | Newsletter mensuelle |
| Guest post | `https://arkforge.fr/arkwatch.html?ref=guestpost` | Articles invités |
| Partnership | `https://arkforge.fr/arkwatch.html?ref=partner` | Partenariats |
| Ads (Google) | `https://arkforge.fr/arkwatch.html?ref=ads_google` | Google Ads |
| Ads (LinkedIn) | `https://arkforge.fr/arkwatch.html?ref=ads_linkedin` | LinkedIn Ads |

## 📝 Exemples d'utilisation

### 1. Post Twitter

```
🚀 ArkWatch surveille vos pages web et vous alerte dès qu'un changement est détecté.

✅ Résumés IA des changements
✅ Gratuit pour 3 URLs
✅ Pas de carte bancaire requise

👉 https://arkforge.fr/arkwatch.html?ref=twitter
```

### 2. Post LinkedIn

```
Vous surveillez vos concurrents, vos clients ou des pages règlementaires ?

ArkWatch automatise ça avec des résumés IA :
- Détection de changements
- Alertes email instantanées
- 3 URLs gratuites

Découvrez : https://arkforge.fr/arkwatch.html?ref=linkedin
```

### 3. Email de prospection

```html
<p>Bonjour [Name],</p>

<p>J'ai remarqué que vous gérez [contexte]. Avez-vous un système pour suivre les changements sur [pages importantes] ?</p>

<p>ArkWatch peut vous faire gagner du temps en surveillant automatiquement ces pages et en vous alertant dès qu'un changement est détecté.</p>

<p><a href="https://arkforge.fr/arkwatch.html?ref=outreach">Découvrir ArkWatch</a> (gratuit pour 3 URLs)</p>
```

### 4. Article guest post

```markdown
## Automatiser la veille web avec ArkWatch

[Contenu de l'article...]

Vous voulez tester ArkWatch ? C'est gratuit pour 3 URLs :
👉 [Essayer ArkWatch](https://arkforge.fr/arkwatch.html?ref=guestpost)
```

### 5. Commentaire sur Reddit

```
I built ArkWatch to solve this exact problem - it monitors web pages and sends you AI summaries when something changes.

Free tier includes 3 URLs monitored daily.

Check it out: https://arkforge.fr/arkwatch.html?ref=reddit
```

## 📈 Consulter les stats

### Accès admin requis

Vous devez avoir une clé API admin pour consulter les analytics.

### Endpoint : GET /api/stats

**Exemple de réponse** :

```json
{
  "total_signups": 42,
  "by_source": {
    "twitter": 15,
    "devto": 12,
    "producthunt": 8,
    "reddit": 5,
    "direct": 2
  },
  "by_day": {
    "2026-02-06": 18,
    "2026-02-07": 24
  }
}
```

### Endpoint : GET /api/stats/funnel

Retourne les métriques de conversion complètes :

```json
{
  "total_signups": 42,
  "email_verified": 28,
  "paid_conversions": 3,
  "verification_rate": 66.67,
  "paid_conversion_rate": 7.14,
  "by_source": {
    "twitter": {
      "signups": 15,
      "verified": 12,
      "paid": 2,
      "verification_rate": 80.0,
      "paid_rate": 13.33
    }
  }
}
```

## 🎨 Créer vos propres paramètres

### Convention de nommage

Format recommandé : `?ref=canal_campagne_detail`

**Exemples** :
- `?ref=ads_google_search_jan2026` → Google Ads, Search, Janvier 2026
- `?ref=partner_acme_webinar` → Partenariat Acme, Webinar
- `?ref=outreach_saas_founders` → Outreach, fondateurs SaaS

### Règles

✅ **À faire** :
- Utiliser des lettres minuscules
- Remplacer les espaces par des underscores `_`
- Être descriptif mais concis
- Rester cohérent dans la nomenclature

❌ **À éviter** :
- Caractères spéciaux (é, à, ç, etc.)
- Espaces
- Noms trop longs (max ~30 caractères)
- Noms génériques ("test", "link", etc.)

## 🔍 Comment vérifier qu'un lien fonctionne

1. Ouvrez le lien dans votre navigateur
2. Inscrivez-vous avec un email de test
3. Contactez un admin pour vérifier que le signup a bien la source correcte

## ⚠️ Erreurs courantes

### Lien sans paramètre

❌ Mauvais : `https://arkforge.fr/arkwatch.html`
→ Sera compté comme "direct"

✅ Bon : `https://arkforge.fr/arkwatch.html?ref=twitter`

### Paramètre mal écrit

❌ Mauvais : `https://arkforge.fr/arkwatch.html?source=twitter`
→ Ne sera pas détecté

✅ Bon : `https://arkforge.fr/arkwatch.html?ref=twitter`

### Caractères spéciaux

❌ Mauvais : `?ref=réseau social`
→ Peut causer des bugs

✅ Bon : `?ref=social`

## 🚀 Quick Start

**Vous postez sur Twitter aujourd'hui ?**

Utilisez ce lien :
```
https://arkforge.fr/arkwatch.html?ref=twitter
```

**Vous envoyez une newsletter ?**

Utilisez ce lien :
```
https://arkforge.fr/arkwatch.html?ref=newsletter
```

**Vous lancez une campagne Google Ads ?**

Utilisez ce lien :
```
https://arkforge.fr/arkwatch.html?ref=ads_google
```

## 📞 Questions ?

Pour toute question sur le tracking ou les analytics, contactez l'équipe technique.

---

**Version** : 1.0
**Dernière mise à jour** : 2026-02-07
**Responsable** : Worker Fondations
