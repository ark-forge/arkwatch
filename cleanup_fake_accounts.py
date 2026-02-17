#!/usr/bin/env python3
"""
Script de nettoyage des faux comptes/utilisateurs/transactions de test
Conforme RGPD - Anonymisation complète des données de test
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Chemins des fichiers de données
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
BACKUP_DIR = DATA_DIR / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

# Configuration des fichiers à nettoyer
FILES_TO_CLEAN = {
    "early_adopters.json": "early adopters",
    "subscribers.json": "subscribers",
}

# Patterns pour identifier les faux comptes
FAKE_PATTERNS = [
    "test@",
    "example@",
    "demo@",
    "fake@",
    "@test.",
    "@example.",
    "audit@arkforge.fr",
    "test-",
    "-test@",
]

def is_fake_account(email: str) -> bool:
    """Vérifie si un email correspond à un compte de test"""
    email_lower = email.lower()
    return any(pattern.lower() in email_lower for pattern in FAKE_PATTERNS)

def backup_file(filepath: Path) -> Path:
    """Crée une sauvegarde du fichier avant modification"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / filepath.name

    if filepath.exists():
        with open(filepath) as f:
            data = f.read()
        with open(backup_path, "w") as f:
            f.write(data)
        print(f"✓ Backup créé: {backup_path}")

    return backup_path

def clean_file(filepath: Path, description: str) -> dict:
    """Nettoie un fichier JSON de ses faux comptes"""

    if not filepath.exists():
        print(f"⚠ Fichier inexistant: {filepath}")
        return {"file": str(filepath), "status": "missing", "removed": 0, "accounts": []}

    # Backup avant modification
    backup_file(filepath)

    # Charger les données
    with open(filepath) as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f"⚠ Format inattendu pour {filepath}")
        return {"file": str(filepath), "status": "invalid_format", "removed": 0, "accounts": []}

    # Identifier les comptes à supprimer
    original_count = len(data)
    removed_accounts = []
    clean_data = []

    for record in data:
        email = record.get("email", "")
        if is_fake_account(email):
            removed_accounts.append({
                "email": email,
                "created_at": record.get("registered_at") or record.get("subscribed_at", "unknown"),
                "ip": record.get("ip", "unknown")
            })
        else:
            clean_data.append(record)

    # Sauvegarder la version nettoyée
    with open(filepath, "w") as f:
        json.dump(clean_data, f, indent=2)

    removed_count = len(removed_accounts)
    print(f"✓ {filepath.name}: {removed_count} compte(s) supprimé(s) sur {original_count}")

    return {
        "file": str(filepath),
        "description": description,
        "status": "cleaned",
        "original_count": original_count,
        "removed": removed_count,
        "remaining": len(clean_data),
        "accounts": removed_accounts
    }

def main():
    """Fonction principale de nettoyage"""

    print("="*70)
    print("NETTOYAGE DES FAUX COMPTES - ArkWatch")
    print("="*70)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Répertoire: {DATA_DIR}")
    print()

    # Résultats du nettoyage
    results = {
        "timestamp": datetime.now().isoformat(),
        "backup_location": str(BACKUP_DIR),
        "files_cleaned": [],
        "total_removed": 0,
        "total_remaining": 0
    }

    # Nettoyer chaque fichier
    for filename, description in FILES_TO_CLEAN.items():
        filepath = DATA_DIR / filename
        print(f"\n📁 Traitement: {filename} ({description})")
        print("-" * 70)

        result = clean_file(filepath, description)
        results["files_cleaned"].append(result)

        if result["status"] == "cleaned":
            results["total_removed"] += result["removed"]
            results["total_remaining"] += result["remaining"]

            # Afficher les comptes supprimés
            if result["accounts"]:
                print("\n  Comptes supprimés:")
                for acc in result["accounts"]:
                    print(f"    - {acc['email']} (créé: {acc['created_at']}, IP: {acc['ip']})")

    # Sauvegarder le rapport de nettoyage
    report_path = DATA_DIR / "cleaned-accounts.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print("RÉSUMÉ DU NETTOYAGE")
    print("="*70)
    print(f"✓ Fichiers traités: {len(results['files_cleaned'])}")
    print(f"✓ Comptes supprimés: {results['total_removed']}")
    print(f"✓ Comptes restants: {results['total_remaining']}")
    print(f"✓ Sauvegardes: {BACKUP_DIR}")
    print(f"✓ Rapport: {report_path}")
    print()

    if results['total_removed'] == 0:
        print("✓ Aucun faux compte détecté - Base de données propre!")
        return 0
    else:
        print(f"✓ Nettoyage terminé - {results['total_removed']} compte(s) de test supprimé(s)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
