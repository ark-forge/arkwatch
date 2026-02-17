#!/usr/bin/env python3
"""
Tests de validation du nettoyage des faux comptes
Vérifie que tous les comptes de test ont bien été supprimés
"""

import json
import sys
from pathlib import Path

# Import du module de chiffrement
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from crypto import decrypt_pii

DATA_DIR = Path(__file__).parent.parent / "data"

# Patterns de détection des faux comptes
FAKE_PATTERNS = [
    "test@", "example@", "demo@", "fake@",
    "@test.", "@example.", "-test@", "test-",
    "audit@arkforge.fr"
]

def is_fake_email(email: str) -> bool:
    """Vérifie si un email est un faux compte"""
    email_lower = email.lower()
    return any(pattern.lower() in email_lower for pattern in FAKE_PATTERNS)

def test_early_adopters_clean():
    """Vérifie qu'il n'y a plus de faux early adopters"""
    filepath = DATA_DIR / "early_adopters.json"

    with open(filepath) as f:
        data = json.load(f)

    fake_count = sum(1 for record in data if is_fake_email(record.get("email", "")))

    assert fake_count == 0, f"❌ {fake_count} faux early adopters détectés"
    print(f"✅ early_adopters.json: {len(data)} comptes, 0 faux comptes")
    return True

def test_subscribers_clean():
    """Vérifie qu'il n'y a plus de faux subscribers"""
    filepath = DATA_DIR / "subscribers.json"

    with open(filepath) as f:
        data = json.load(f)

    fake_count = sum(1 for record in data if is_fake_email(record.get("email", "")))

    assert fake_count == 0, f"❌ {fake_count} faux subscribers détectés"
    print(f"✅ subscribers.json: {len(data)} comptes, 0 faux comptes")
    return True

def test_api_keys_clean():
    """Vérifie qu'il n'y a plus de faux comptes dans les API keys"""
    filepath = DATA_DIR / "api_keys.json"

    if not filepath.exists():
        print(f"⚠️  api_keys.json n'existe pas")
        return True

    with open(filepath) as f:
        data = json.load(f)

    fake_count = 0
    for key_hash, key_data in data.items():
        try:
            email_enc = key_data.get("email", "")
            if email_enc and email_enc.startswith("enc:"):
                email = decrypt_pii(email_enc)
                if is_fake_email(email):
                    fake_count += 1
                    print(f"  ⚠️  Faux compte détecté: {email}")
        except Exception as e:
            # Skip si déchiffrement échoue
            pass

    assert fake_count == 0, f"❌ {fake_count} faux comptes API détectés"
    print(f"✅ api_keys.json: {len(data)} clés, 0 faux comptes")
    return True

def test_watches_clean():
    """Vérifie qu'il n'y a plus de faux comptes dans les watches"""
    filepath = DATA_DIR / "watches.json"

    if not filepath.exists():
        print(f"⚠️  watches.json n'existe pas")
        return True

    with open(filepath) as f:
        data = json.load(f)

    fake_count = 0
    for watch in data:
        try:
            # Vérifier user_email et notify_email
            for field in ["user_email", "notify_email"]:
                email_enc = watch.get(field, "")
                if email_enc and email_enc.startswith("enc:"):
                    email = decrypt_pii(email_enc)
                    if is_fake_email(email):
                        fake_count += 1
                        print(f"  ⚠️  Faux compte détecté dans watch {watch['id']}: {email}")
                        break
        except Exception as e:
            # Skip si déchiffrement échoue
            pass

    assert fake_count == 0, f"❌ {fake_count} faux comptes dans watches détectés"
    print(f"✅ watches.json: {len(data)} watches, 0 faux comptes")
    return True

def test_cleanup_report_exists():
    """Vérifie que le rapport de nettoyage existe"""
    report_path = DATA_DIR / "cleaned-accounts.json"

    assert report_path.exists(), "❌ Rapport de nettoyage manquant"

    with open(report_path) as f:
        report = json.load(f)

    assert "timestamp" in report, "❌ Rapport invalide: timestamp manquant"
    assert "files_cleaned" in report, "❌ Rapport invalide: files_cleaned manquant"
    assert "total_removed" in report, "❌ Rapport invalide: total_removed manquant"

    print(f"✅ Rapport de nettoyage: {report['total_removed']} comptes supprimés")
    return True

def test_backups_exist():
    """Vérifie que les sauvegardes ont été créées"""
    backup_dir = DATA_DIR / "backups"

    assert backup_dir.exists(), "❌ Répertoire de backup manquant"

    # Trouver le backup le plus récent
    backup_dirs = sorted(backup_dir.glob("*"), reverse=True)
    assert len(backup_dirs) > 0, "❌ Aucun backup trouvé"

    latest_backup = backup_dirs[0]
    backup_files = list(latest_backup.glob("*.json"))

    assert len(backup_files) > 0, "❌ Backup vide"

    print(f"✅ Backups: {len(backup_files)} fichiers dans {latest_backup.name}")
    return True

def main():
    """Exécute tous les tests de validation"""
    print("="*70)
    print("VALIDATION DU NETTOYAGE DES FAUX COMPTES")
    print("="*70)
    print()

    tests = [
        ("Early Adopters", test_early_adopters_clean),
        ("Subscribers", test_subscribers_clean),
        ("API Keys", test_api_keys_clean),
        ("Watches", test_watches_clean),
        ("Rapport de nettoyage", test_cleanup_report_exists),
        ("Backups", test_backups_exist),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n🧪 Test: {test_name}")
        print("-" * 70)
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            failed += 1

    print("\n" + "="*70)
    print("RÉSULTATS")
    print("="*70)
    print(f"✅ Tests réussis: {passed}/{len(tests)}")
    print(f"❌ Tests échoués: {failed}/{len(tests)}")
    print()

    if failed == 0:
        print("✅ VALIDATION COMPLÈTE - Tous les faux comptes ont été supprimés")
        return 0
    else:
        print("❌ VALIDATION ÉCHOUÉE - Des faux comptes subsistent")
        return 1

if __name__ == "__main__":
    sys.exit(main())
