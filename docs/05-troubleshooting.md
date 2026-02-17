# ArkWatch - Troubleshooting

Guide de résolution des problèmes courants.

---

## Erreurs d'authentification

### Erreur 401 : "Missing or invalid API key"

**Cause** : La clé API est absente ou invalide.

**Solution** :

1. Vérifiez que vous transmettez la clé dans le header `X-API-Key` :
   ```bash
   curl -H "X-API-Key: ak_VOTRE_CLE" https://watch.arkforge.fr/api/v1/watches
   ```
2. Vérifiez que la clé commence bien par `ak_`
3. Si vous avez perdu votre clé, vous devez créer un nouveau compte

### Erreur 403 : "Email not verified"

**Cause** : Votre email n'a pas été vérifié.

**Solution** :

1. Vérifiez votre boîte mail pour le code à 6 chiffres
2. Vérifiez avec :
   ```bash
   curl -X POST https://watch.arkforge.fr/api/v1/auth/verify-email \
     -H "Content-Type: application/json" \
     -d '{"email": "votre@email.com", "code": "123456"}'
   ```
3. Si le code a expiré (>24h), renvoyez-le :
   ```bash
   curl -X POST https://watch.arkforge.fr/api/v1/auth/resend-verification \
     -H "Content-Type: application/json" \
     -d '{"email": "votre@email.com"}'
   ```

### Erreur 409 : "Email already registered"

**Cause** : Un compte existe déjà avec cette adresse email.

**Solution** :

- Utilisez la clé API que vous avez reçue lors de l'inscription initiale
- Si vous l'avez perdue, supprimez le compte existant et réinscrivez-vous

---

## Erreurs de création de Watch

### Erreur 400 : "URL not allowed"

**Cause** : L'URL est bloquée par la protection SSRF.

**Solution** :

- Utilisez uniquement des URLs publiques HTTPS
- Les adresses IP privées (localhost, 127.0.0.1, 10.x.x.x, 192.168.x.x) sont interdites
- Vérifiez que l'URL est bien formée : `https://example.com/page`

### Erreur 403 : "Watch limit exceeded"

**Cause** : Vous avez atteint la limite de watches de votre plan.

**Solution** :

1. Vérifiez votre utilisation :
   ```bash
   curl -H "X-API-Key: ak_VOTRE_CLE" \
     https://watch.arkforge.fr/api/v1/billing/usage
   ```
2. Supprimez des watches inutiles, ou
3. Passez à un plan supérieur :
   ```bash
   curl -X POST https://watch.arkforge.fr/api/v1/billing/checkout \
     -H "X-API-Key: ak_VOTRE_CLE" \
     -H "Content-Type: application/json" \
     -d '{"tier": "starter"}'
   ```

---

## Erreurs de rate limiting

### Erreur 429 : "Too Many Requests"

**Cause** : Vous avez dépassé le nombre de requêtes autorisées.

**Limites** :

| Endpoint | Limite | Fenêtre |
|---|---|---|
| Register | 3 par IP | 1 heure |
| Verify email | 5 par email | 15 min |
| Resend verification | 3 par IP | 1 heure |

**Solution** : Attendez que la fenêtre de temps soit écoulée avant de réessayer.

---

## Problèmes de Watches

### Mon watch est en statut "error"

**Causes possibles** :

1. La page surveillée est temporairement inaccessible
2. L'URL a changé (redirection permanente)
3. Le site bloque les requêtes automatisées

**Solution** :

1. Vérifiez que l'URL est toujours accessible dans votre navigateur
2. Si l'URL a changé, mettez à jour le watch ou créez-en un nouveau
3. Le watch reprendra automatiquement lors de la prochaine vérification si la page redevient accessible

### Mon watch ne détecte pas les changements

**Causes possibles** :

1. Le seuil `min_change_ratio` est trop élevé
2. Les changements sont en dessous du seuil
3. Le watch est en pause

**Solution** :

1. Baissez le seuil de changement :
   ```bash
   curl -X PATCH https://watch.arkforge.fr/api/v1/watches/WATCH_ID \
     -H "X-API-Key: ak_VOTRE_CLE" \
     -H "Content-Type: application/json" \
     -d '{"min_change_ratio": 0.01}'
   ```
2. Vérifiez le statut du watch :
   ```bash
   curl -H "X-API-Key: ak_VOTRE_CLE" \
     https://watch.arkforge.fr/api/v1/watches/WATCH_ID
   ```

### Les rapports ne contiennent pas de résumé IA

**Cause** : L'analyse IA peut échouer si le changement est trop petit ou si le service IA est temporairement indisponible.

**Solution** : Vérifiez le champ `diff` du rapport pour les changements bruts. Le résumé IA sera disponible lors du prochain rapport.

---

## Problèmes d'emails

### Je ne reçois pas le code de vérification

1. Vérifiez votre dossier spam/indésirables
2. Vérifiez que l'adresse email est correcte
3. Renvoyez le code :
   ```bash
   curl -X POST https://watch.arkforge.fr/api/v1/auth/resend-verification \
     -H "Content-Type: application/json" \
     -d '{"email": "votre@email.com"}'
   ```
4. Attendez quelques minutes (le rate limit autorise 3 envois par heure)

### Je ne reçois pas les alertes de changement

1. Vérifiez que votre email est vérifié
2. Vérifiez que vous n'êtes pas désinscrit
3. Vérifiez le `notify_email` du watch :
   ```bash
   curl -H "X-API-Key: ak_VOTRE_CLE" \
     https://watch.arkforge.fr/api/v1/watches/WATCH_ID
   ```
4. Vérifiez que le watch est `active`
5. Vérifiez votre dossier spam

---

## Problèmes de facturation

### Je n'arrive pas à upgrader mon plan

1. Vérifiez que votre email est vérifié
2. Créez une session de paiement :
   ```bash
   curl -X POST https://watch.arkforge.fr/api/v1/billing/checkout \
     -H "X-API-Key: ak_VOTRE_CLE" \
     -H "Content-Type: application/json" \
     -d '{"tier": "starter"}'
   ```
3. Ouvrez l'URL `checkout_url` retournée dans votre navigateur

### Mon abonnement n'est pas pris en compte

Après le paiement Stripe, la mise à jour peut prendre quelques secondes. Vérifiez :

```bash
curl -H "X-API-Key: ak_VOTRE_CLE" \
  https://watch.arkforge.fr/api/v1/billing/subscription
```

Si le problème persiste, accédez au portail Stripe pour vérifier le statut :

```bash
curl -X POST https://watch.arkforge.fr/api/v1/billing/portal \
  -H "X-API-Key: ak_VOTRE_CLE"
```

---

## Problèmes API généraux

### L'API ne répond pas

1. Vérifiez l'état de l'API :
   ```bash
   curl https://watch.arkforge.fr/health
   ```
2. Si la réponse est `{"status": "healthy"}`, l'API fonctionne
3. Si pas de réponse, le service est peut-être en maintenance

### Erreur 500 : "Internal Server Error"

**Cause** : Erreur interne du serveur.

**Solution** :

- Réessayez la requête après quelques secondes
- Si le problème persiste, vérifiez `/health` et `/ready`
- Contactez le support si nécessaire

---

## Besoin d'aide supplémentaire ?

Si votre problème n'est pas couvert ici, contactez-nous à **contact@arkforge.fr**.
