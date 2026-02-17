# Guide Création Trial Guidé Manuel - ArkWatch

**Créé**: 2026-02-09
**Usage**: Procédure pour créer manuellement un compte trial pour un prospect
**Temps estimé**: 10 min

---

## 🎯 Objectif

Créer manuellement un compte trial ArkWatch pour un prospect qui a manifesté son intérêt, sans passer par le formulaire automatique de signup.

**Pourquoi manuel ?**
- Plus de contrôle sur l'onboarding
- Permet de personnaliser le tier et la durée
- Facilite le suivi et le support direct
- Meilleure expérience pour les premiers clients

---

## 📋 Prérequis

- [ ] Email du prospect validé
- [ ] Tier choisi (Starter/Pro/Business)
- [ ] Durée du trial (défaut: 14 jours, peut être prolongé)
- [ ] Accès SSH au serveur ArkWatch (`watch.arkforge.fr`)

---

## 🚀 Procédure Étape par Étape

### Étape 1: Se connecter au serveur ArkWatch

```bash
# SSH au serveur
ssh ubuntu@watch.arkforge.fr

# Naviguer vers le dossier API
cd /opt/arkwatch/api

# Activer l'environnement Python
source venv/bin/activate
```

---

### Étape 2: Créer le user trial manuellement

#### Option A: Via script admin (RECOMMANDÉ)

```bash
# Créer trial user avec script admin
python3 scripts/create_trial_user.py \
    --email prospect@company.com \
    --tier pro \
    --trial-days 14 \
    --name "John Doe"  # optionnel

# Le script retourne:
# ✅ User created: prospect@company.com
# ✅ API Key: ak_live_ABC123XYZ456
# ✅ Trial ends: 2026-02-23T10:00:00Z
# ✅ Dashboard: https://watch.arkforge.fr/dashboard
```

**Si le script n'existe pas**, créer le fichier `scripts/create_trial_user.py` :

```python
#!/usr/bin/env python3
"""Create trial user manually for ArkWatch prospects."""

import argparse
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent dir to path to import from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db
from src.auth.api_keys import generate_api_key, hash_api_key
from src.billing.stripe_service import StripeService


def create_trial_user(email: str, tier: str, trial_days: int, name: str = None):
    """Create trial user with specified tier and duration."""

    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    # Calculate trial end date
    trial_ends_at = datetime.now(timezone.utc) + timedelta(days=trial_days)

    # Create Stripe customer
    stripe_service = StripeService()
    customer_id = stripe_service.create_customer(
        email=email,
        name=name or email.split("@")[0].capitalize(),
        api_key_hash=api_key_hash
    )

    # Insert user in database
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            email, api_key_hash, tier, subscription_status,
            stripe_customer_id, trial_ends_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email,
            api_key_hash,
            tier,
            "trialing",
            customer_id,
            trial_ends_at.isoformat(),
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()

    print(f"✅ User created: {email}")
    print(f"✅ API Key: {api_key}")
    print(f"✅ Trial ends: {trial_ends_at.isoformat()}")
    print(f"✅ Tier: {tier}")
    print(f"✅ Stripe Customer ID: {customer_id}")
    print(f"✅ Dashboard: https://watch.arkforge.fr/dashboard")

    return {
        "email": email,
        "api_key": api_key,
        "tier": tier,
        "trial_ends_at": trial_ends_at.isoformat(),
        "customer_id": customer_id
    }


def main():
    parser = argparse.ArgumentParser(description="Create trial user for ArkWatch")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--tier", required=True, choices=["starter", "pro", "business"], help="Subscription tier")
    parser.add_argument("--trial-days", type=int, default=14, help="Trial duration in days (default: 14)")
    parser.add_argument("--name", help="User name (optional)")

    args = parser.parse_args()

    result = create_trial_user(args.email, args.tier, args.trial_days, args.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Rendre le script exécutable** :
```bash
chmod +x scripts/create_trial_user.py
```

---

#### Option B: Via SQL direct (si script indisponible)

```bash
# Se connecter à la DB SQLite
sqlite3 /opt/arkwatch/api/data/arkwatch.db

# Générer API key (faire en Python)
python3 -c "
import secrets
import hashlib
api_key = 'ak_live_' + secrets.token_urlsafe(32)
api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
print(f'API Key: {api_key}')
print(f'Hash: {api_key_hash}')
"

# Insérer user dans DB
INSERT INTO users (
    email,
    api_key_hash,
    tier,
    subscription_status,
    trial_ends_at,
    created_at
) VALUES (
    'prospect@company.com',
    '[HASH_FROM_ABOVE]',
    'pro',
    'trialing',
    datetime('now', '+14 days'),
    datetime('now')
);

# Vérifier insertion
SELECT email, tier, subscription_status, trial_ends_at FROM users WHERE email = 'prospect@company.com';

# Quitter SQLite
.quit
```

---

### Étape 3: Créer Stripe Customer (si pas fait automatiquement)

```bash
# Se connecter au serveur Python
python3

# Importer Stripe
import stripe
stripe.api_key = "sk_live_REDACTED"

# Créer customer
customer = stripe.Customer.create(
    email="prospect@company.com",
    name="John Doe",
    description="ArkWatch trial - Manual creation"
)

print(f"Customer ID: {customer.id}")

# Mettre à jour la DB avec customer_id
import sqlite3
db = sqlite3.connect("/opt/arkwatch/api/data/arkwatch.db")
cursor = db.cursor()
cursor.execute(
    "UPDATE users SET stripe_customer_id = ? WHERE email = ?",
    (customer.id, "prospect@company.com")
)
db.commit()
print("✅ Customer ID saved to DB")

# Quitter Python
exit()
```

---

### Étape 4: Vérifier la création

```bash
# Vérifier user dans DB
sqlite3 /opt/arkwatch/api/data/arkwatch.db "SELECT email, tier, subscription_status, trial_ends_at, stripe_customer_id FROM users WHERE email = 'prospect@company.com';"

# Expected output:
# prospect@company.com|pro|trialing|2026-02-23T10:00:00Z|cus_ABC123

# Vérifier dans logs API
tail -n 50 /opt/arkwatch/api/logs/api.log | grep prospect@company.com
```

---

### Étape 5: Envoyer credentials au prospect

**Email template** :

```
Sujet: Votre accès ArkWatch est prêt ! 🚀

Bonjour [Prénom],

Votre compte trial ArkWatch est maintenant actif pour 14 jours. Voici vos accès :

🔑 **Credentials** :
- Email : prospect@company.com
- API Key : ak_live_ABC123XYZ456
- Dashboard : https://watch.arkforge.fr/dashboard
- Documentation : https://arkforge.fr/docs

📅 **Trial valable jusqu'au** : 23 février 2026

🎯 **Quick Start** :
1. Connectez-vous au dashboard avec votre API key
2. Créez votre premier monitor en 30 secondes
3. Configurez vos alertes email
4. Testez la détection de changements en temps réel

🆘 **Besoin d'aide ?**
Répondez simplement à cet email, je suis là pour vous aider (réponse < 4h).

Je peux aussi vous proposer une démo rapide de 15 min sur Zoom si vous préférez.

Bon trial !

Cordialement,
[Votre nom]
ArkWatch by ArkForge
https://arkforge.fr

---
Note : Votre API key est confidentielle, ne la partagez pas.
```

---

## 🔧 Commandes Utiles

### Vérifier statut d'un user

```bash
ssh ubuntu@watch.arkforge.fr
cd /opt/arkwatch/api
source venv/bin/activate

python3 scripts/get_user_stats.py --email prospect@company.com

# Retourne:
# Email: prospect@company.com
# Tier: pro
# Status: trialing
# Trial ends: 2026-02-23T10:00:00Z
# Monitors: 3
# Watches: 8
# Alerts configured: 5
# Last activity: 2026-02-10T15:30:00Z
```

---

### Prolonger un trial

```bash
# Via SQL
sqlite3 /opt/arkwatch/api/data/arkwatch.db

UPDATE users
SET trial_ends_at = datetime('now', '+21 days')
WHERE email = 'prospect@company.com';

SELECT email, trial_ends_at FROM users WHERE email = 'prospect@company.com';

.quit
```

---

### Upgrader un trial vers payant (après paiement)

```bash
# Via SQL
sqlite3 /opt/arkwatch/api/data/arkwatch.db

UPDATE users
SET
    subscription_status = 'active',
    trial_ends_at = NULL,
    stripe_subscription_id = 'sub_ABC123'
WHERE email = 'prospect@company.com';

.quit
```

---

## ⚠️ Erreurs Courantes

### Erreur: "Email already exists"

```bash
# Vérifier si user existe déjà
sqlite3 /opt/arkwatch/api/data/arkwatch.db "SELECT email, subscription_status FROM users WHERE email = 'prospect@company.com';"

# Si oui, soit:
# 1. Utiliser email existant
# 2. Supprimer user (attention aux données)
# 3. Réactiver trial
```

### Erreur: "Stripe API key invalid"

```bash
# Vérifier API key dans .env.stripe
cat /opt/arkwatch/api/.env.stripe | grep STRIPE_SECRET_KEY

# Tester API key
python3 -c "
import stripe
stripe.api_key = 'sk_live_...'
print(stripe.Customer.list(limit=1))
"
```

### Erreur: "Database locked"

```bash
# Attendre que d'autres processus se terminent
# Ou redémarrer API
sudo systemctl restart arkwatch-api
```

---

## 📊 Tracking

Après création du trial, logger dans `conversion_tracker.csv` :

```csv
prospect@company.com,manual_trial,2026-02-09T10:00:00Z,trial_active,2026-02-09T10:30:00Z,2026-02-09T11:00:00Z,2026-02-23T11:00:00Z,no,,,pro,,Manual trial creation for warm lead
```

---

## 🔄 Prochaines Étapes

Après création du trial :
1. ✅ Envoyer email avec credentials
2. ✅ Logger dans conversion_tracker.csv
3. ✅ Planifier check-in J+3
4. ✅ Proposer démo si demandée
5. ✅ Suivre checklist onboarding_checklist.md

---

*Guide créé par Worker Fondations - Task #20260903*
