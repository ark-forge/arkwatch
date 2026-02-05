#!/usr/bin/env python3
"""
Pre-deployment validation script for ArkWatch.
RULE: No deployment without passing tests.

This script:
1. Runs unit tests
2. Checks /health endpoint
3. Validates critical imports
4. Returns exit code for CI/CD integration
"""
import subprocess
import sys
import os
import httpx
import time

# Configuration
ARKWATCH_DIR = "/opt/claude-ceo/workspace/arkwatch"
API_URL = os.environ.get("ARKWATCH_API_URL", "http://localhost:8080")
HEALTH_TIMEOUT = 10
TEST_TIMEOUT = 120


def run_tests() -> tuple[bool, str]:
    """Run pytest suite"""
    print("=" * 50)
    print("ÉTAPE 1: Exécution des tests unitaires")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                f"{ARKWATCH_DIR}/tests",
                "-v",
                "--tb=short",
                "-x",  # Stop on first failure
            ],
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT,
            cwd=ARKWATCH_DIR,
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            return True, "Tests passés"
        else:
            return False, f"Tests échoués (code: {result.returncode})"

    except subprocess.TimeoutExpired:
        return False, f"Tests timeout après {TEST_TIMEOUT}s"
    except Exception as e:
        return False, f"Erreur tests: {str(e)}"


def check_health_endpoint() -> tuple[bool, str]:
    """Check if /health endpoint responds"""
    print("\n" + "=" * 50)
    print("ÉTAPE 2: Vérification endpoint /health")
    print("=" * 50)

    try:
        response = httpx.get(
            f"{API_URL}/health",
            timeout=HEALTH_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print(f"✓ /health OK: {data}")
                return True, "Health check passé"
            else:
                return False, f"Status inattendu: {data}"
        else:
            return False, f"HTTP {response.status_code}"

    except httpx.ConnectError:
        return False, "API non accessible (connexion refusée)"
    except httpx.TimeoutException:
        return False, f"Timeout après {HEALTH_TIMEOUT}s"
    except Exception as e:
        return False, f"Erreur health check: {str(e)}"


def check_imports() -> tuple[bool, str]:
    """Validate critical imports work"""
    print("\n" + "=" * 50)
    print("ÉTAPE 3: Validation des imports critiques")
    print("=" * 50)

    try:
        sys.path.insert(0, ARKWATCH_DIR)

        from src.scraper.scraper import WebScraper
        from src.analyzer.analyzer import ContentAnalyzer
        from src.storage.database import Database
        from src.api.main import app

        print("✓ WebScraper importé")
        print("✓ ContentAnalyzer importé")
        print("✓ Database importé")
        print("✓ FastAPI app importé")

        return True, "Imports OK"

    except ImportError as e:
        return False, f"Import échoué: {str(e)}"
    except Exception as e:
        return False, f"Erreur imports: {str(e)}"


def main() -> int:
    """Main validation routine"""
    print("╔══════════════════════════════════════════════════╗")
    print("║  ARKWATCH PRE-DEPLOYMENT VALIDATION              ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  Règle: Aucun déploiement sans test passé        ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    results = []

    # Step 1: Run tests
    success, msg = run_tests()
    results.append(("Tests unitaires", success, msg))

    # Step 2: Check imports (even if tests fail)
    success, msg = check_imports()
    results.append(("Imports critiques", success, msg))

    # Step 3: Health check (optional - API might not be running)
    if "--skip-health" not in sys.argv:
        success, msg = check_health_endpoint()
        results.append(("Health endpoint", success, msg))
    else:
        print("\n[INFO] Health check skipped (--skip-health)")

    # Summary
    print("\n" + "=" * 50)
    print("RÉSUMÉ VALIDATION")
    print("=" * 50)

    all_passed = True
    critical_failed = False

    for name, success, msg in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} | {name}: {msg}")

        # Tests are critical - must pass
        if name == "Tests unitaires" and not success:
            critical_failed = True
            all_passed = False
        # Imports are critical
        elif name == "Imports critiques" and not success:
            critical_failed = True
            all_passed = False
        # Health check is warning only (API might not be running)
        elif not success:
            all_passed = False

    print()
    if critical_failed:
        print("╔══════════════════════════════════════════════════╗")
        print("║  ✗ DÉPLOIEMENT BLOQUÉ - Tests critiques échoués  ║")
        print("╚══════════════════════════════════════════════════╝")
        return 1
    elif not all_passed:
        print("╔══════════════════════════════════════════════════╗")
        print("║  ⚠ ATTENTION - Certaines vérifications échouées  ║")
        print("║  Déploiement autorisé avec prudence              ║")
        print("╚══════════════════════════════════════════════════╝")
        return 0
    else:
        print("╔══════════════════════════════════════════════════╗")
        print("║  ✓ VALIDATION COMPLÈTE - Déploiement autorisé    ║")
        print("╚══════════════════════════════════════════════════╝")
        return 0


if __name__ == "__main__":
    sys.exit(main())
