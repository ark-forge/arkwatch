# Test End-to-End ArkWatch - Rapport Complet

**Date**: 2026-02-06 21:53-21:56 UTC
**Testeur**: Worker Croissance (automatisé)
**Task ID**: 20260473

---

## Parcours testé

Landing → Signup → Vérification email → Dashboard → Premier monitor

---

## Résultats par étape

### Étape 1: Landing Page (arkforge.fr/arkwatch.html)
| Critère | Résultat |
|---------|----------|
| Page accessible | OK |
| Contenu affiché | OK - Hero, features, pricing, signup form |
| CTA "Commencer gratuitement" | OK → pointe vers /register.html |
| Lien Dashboard | OK → /dashboard.html |
| Lien API Docs | OK → /api-docs.html |
| Pricing affiché | OK - 4 tiers (Free, Starter, Pro, Business) |
| Banner beta | OK - "Free beta - 3 free URLs, no credit card" |

**Verdict: PASS**

---

### Étape 2: Page d'inscription (arkforge.fr/register.html)
| Critère | Résultat |
|---------|----------|
| Page accessible | OK |
| Formulaire avec champs | OK - Nom, Email, Case privacy |
| 3 étapes visuelles | OK - Inscription → Vérification → Clé API |
| Lien "Déjà inscrit?" | OK → /dashboard.html |
| Soumission POST vers API | OK → watch.arkforge.fr/api/v1/auth/register |

**Verdict: PASS**

---

### Étape 3: Création de compte (API register)
| Critère | Résultat |
|---------|----------|
| POST /api/v1/auth/register | OK - 200 |
| API key retournée | OK - format ak_xxx |
| Message de bienvenue | OK |
| Email vérification envoyé | OK (best-effort via email_sender.py) |
| Doublon email rejeté | OK - "Email already registered" |
| Privacy non acceptée rejetée | OK - message clair |
| Validation email format | OK (via Pydantic) |

**Données reçues:**
```json
{
  "api_key": "ak_u-Ja-V4SzzBtRo9ZV_adJmuD_R33IgpxW2UroZAE35c",
  "email": "test-e2e-20260206@yopmail.com",
  "tier": "free",
  "message": "Welcome! A verification code has been sent..."
}
```

**Verdict: PASS**

---

### Étape 3b: Vérification email
| Critère | Résultat |
|---------|----------|
| Code 6 chiffres envoyé par email | OK |
| POST /verify-email avec code | OK - 200 "Email verified successfully" |
| Resend code fonctionne | OK |

**BLOCAGE POTENTIEL**: Le code de vérification est envoyé par email. Si l'email n'arrive pas (spam, délai), l'utilisateur est bloqué. Pas de message de fallback ni d'aide visible sur la page.

**Verdict: PASS (avec réserve)**

---

### Étape 4: Dashboard (arkforge.fr/dashboard.html)
| Critère | Résultat |
|---------|----------|
| Page accessible | OK |
| Login par API key | OK - champ ak_xxx |
| GET /api/v1/watches | OK - [] (vide au départ) |
| GET /api/v1/auth/account/data | OK - données RGPD |
| GET /api/v1/billing/usage | OK - tier free, 0/3 watches |
| Onglets Mes URLs / Rapports / Compte | OK |
| Bouton "+ Ajouter une URL" | OK |
| Lien signup pour non-inscrits | OK |

**Important**: Les endpoints /watches et /billing/usage fonctionnent MÊME SANS vérification email. Seule la CRÉATION de watch est bloquée.

**Verdict: PASS**

---

### Étape 5: Création premier monitor
| Critère | Résultat |
|---------|----------|
| SANS vérification email | KO - 403 "Email not verified" |
| AVEC vérification email | OK - 200, monitor créé |
| Watch apparaît dans la liste | OK |
| Usage mis à jour (1/3) | OK |
| Status "active" | OK |

**Données reçues:**
```json
{
  "id": "26b8a628-9795-42e3-8040-e9c9a4b9025e",
  "name": "Test Monitor E2E",
  "url": "https://example.com/",
  "check_interval": 86400,
  "status": "active"
}
```

**Verdict: PASS**

---

### Étape 6: Nettoyage
| Critère | Résultat |
|---------|----------|
| DELETE /api/v1/auth/account | OK - Compte et watches supprimés |
| RGPD Art.17 respecté | OK |

---

## BLOCAGES IDENTIFIÉS

### BLOCAGE 1 (CRITIQUE): Friction de la vérification email
- **Impact**: Un utilisateur qui ne reçoit PAS l'email de vérification ne peut PAS créer de monitor
- **Constat**: L'email est envoyé en "best-effort" (fire-and-forget, pas de retry, pas de log d'erreur)
- **Risque**: Emails en spam, délai de livraison, adresse incorrecte → utilisateur perdu
- **Solution recommandée**:
  1. Ajouter un log quand l'envoi échoue
  2. Afficher un message d'aide ("Vérifiez vos spams", "Renvoyer le code")
  3. Option: permettre de créer 1 watch sans vérification (et bloquer les alertes email)

### BLOCAGE 2 (MOYEN): Rate limiting trop agressif pour les tests
- **Impact**: Nginx retourne 429 après ~3 requêtes rapides depuis la même IP
- **Constat**: Un utilisateur normal ne sera probablement pas affecté, mais les tests automatisés et les développeurs le seront
- **Solution**: Le rate limiting actuel est OK pour la prod, mais ajouter un header Retry-After serait utile

### BLOCAGE 3 (MINEUR): Redirect 307 sur /api/v1/pricing
- **Impact**: Le endpoint pricing fait un redirect 307 (trailing slash). Les clients doivent suivre le redirect.
- **Constat**: Fonctionne avec `-L` mais peut poser problème à certains clients HTTP basiques
- **Solution**: Ajouter `redirect_slashes=False` dans FastAPI ou uniformiser les routes

### BLOCAGE 4 (UX): Perte de la clé API = compte perdu
- **Impact**: Si l'utilisateur perd sa clé API après inscription, il n'y a pas de mécanisme de récupération
- **Constat**: Le message d'erreur pour email dupliqué dit "Contact contact@arkforge.fr if you lost your key"
- **Solution recommandée**: Ajouter un endpoint "forgot API key" qui renvoie la clé par email (ou en génère une nouvelle)

### BLOCAGE 5 (UX): Pas de robots.txt
- **Impact**: Les bots rencontrent un 404 sur /robots.txt (visible dans les logs)
- **Solution**: Ajouter un robots.txt minimal

---

## RÉSUMÉ DU PARCOURS

```
Landing (arkforge.fr/arkwatch.html)     ✅ OK
  ↓ CTA "Commencer gratuitement"
Register (arkforge.fr/register.html)    ✅ OK
  ↓ Formulaire Nom + Email + Privacy
API Register                            ✅ OK → API key reçue
  ↓ Email avec code 6 chiffres
Vérification email                      ⚠️ OK mais friction (email delivery)
  ↓ API key dans localStorage
Dashboard (arkforge.fr/dashboard.html)  ✅ OK
  ↓ Bouton "+ Ajouter une URL"
Création monitor                        ✅ OK (après vérification email)
```

**Temps total du parcours**: ~2 minutes (hors attente email)

---

## RECOMMANDATIONS PRIORITAIRES

1. **P0** - Fiabiliser l'envoi d'emails de vérification (logging, retry, monitoring)
2. **P1** - Ajouter un mécanisme de récupération de clé API ("forgot key")
3. **P1** - Ajouter robots.txt pour éviter les 404 crawlers
4. **P2** - Supprimer le redirect 307 sur les endpoints API
5. **P2** - Ajouter un message d'aide sur la page de vérification ("Vérifiez vos spams")
