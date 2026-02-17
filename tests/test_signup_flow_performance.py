#!/usr/bin/env python3
"""
Test du parcours complet signup → dashboard en < 30 secondes
Vérifie la performance du funnel de conversion
"""

import time
import random
import string
import requests
from datetime import datetime

API_BASE = "https://watch.arkforge.fr/api/v1"
DASHBOARD_URL = "https://arkforge.fr/dashboard.html"


def generate_test_email():
    """Génère un email de test unique"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_arkwatch_{random_str}@example.com"


def test_signup_flow_performance():
    """Test complet du parcours signup → dashboard"""
    print("=" * 60)
    print("TEST: Parcours signup → dashboard (objectif < 30s)")
    print("=" * 60)

    start_time = time.time()

    # Étape 1: Générer les données de test
    test_email = generate_test_email()
    test_name = "Test User"

    print(f"\n[{time.time() - start_time:.2f}s] Données de test générées")
    print(f"  Email: {test_email}")
    print(f"  Name: {test_name}")

    # Étape 2: Inscription (POST /auth/register)
    step2_start = time.time()
    try:
        response = requests.post(
            f"{API_BASE}/auth/register",
            json={
                "email": test_email,
                "name": test_name,
                "privacy_accepted": True
            },
            timeout=10
        )
        step2_duration = time.time() - step2_start

        print(f"\n[{time.time() - start_time:.2f}s] POST /auth/register")
        print(f"  Status: {response.status_code}")
        print(f"  Duration: {step2_duration:.2f}s")

        if response.status_code != 200:
            print(f"  ❌ ÉCHEC: {response.text}")
            return False

        data = response.json()
        api_key = data.get("api_key")
        if not api_key:
            print("  ❌ ÉCHEC: Pas de clé API retournée")
            return False

        print(f"  ✓ API Key reçue: {api_key[:20]}...")

    except Exception as e:
        print(f"  ❌ ERREUR: {e}")
        return False

    # Étape 3: Vérifier l'accès au dashboard
    step3_start = time.time()
    try:
        response = requests.get(DASHBOARD_URL, timeout=5)
        step3_duration = time.time() - step3_start

        print(f"\n[{time.time() - start_time:.2f}s] GET /dashboard.html")
        print(f"  Status: {response.status_code}")
        print(f"  Duration: {step3_duration:.2f}s")

        if response.status_code != 200:
            print(f"  ❌ ÉCHEC: Dashboard inaccessible")
            return False

        print(f"  ✓ Dashboard accessible")

    except Exception as e:
        print(f"  ❌ ERREUR: {e}")
        return False

    # Étape 4: Tester l'API avec la clé (GET /watches)
    step4_start = time.time()
    try:
        response = requests.get(
            f"{API_BASE}/watches",
            headers={"X-API-Key": api_key},
            timeout=10
        )
        step4_duration = time.time() - step4_start

        print(f"\n[{time.time() - start_time:.2f}s] GET /watches (test API key)")
        print(f"  Status: {response.status_code}")
        print(f"  Duration: {step4_duration:.2f}s")

        if response.status_code != 200:
            print(f"  ❌ ÉCHEC: API key non fonctionnelle")
            return False

        watches = response.json()
        print(f"  ✓ API key fonctionnelle (watches: {len(watches)})")

    except Exception as e:
        print(f"  ❌ ERREUR: {e}")
        return False

    # Résultat final
    total_duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("RÉSULTAT")
    print("=" * 60)
    print(f"Durée totale: {total_duration:.2f}s")
    print(f"Objectif: < 30s")

    if total_duration < 30:
        print(f"✅ SUCCÈS - Parcours complet en {total_duration:.2f}s")
        print(f"   Marge: {30 - total_duration:.2f}s sous l'objectif")
        return True
    else:
        print(f"❌ ÉCHEC - Parcours trop lent ({total_duration:.2f}s)")
        print(f"   Dépassement: {total_duration - 30:.2f}s")
        return False


def test_cta_visibility():
    """Teste la visibilité du CTA sur la landing page"""
    print("\n" + "=" * 60)
    print("TEST: Visibilité du CTA sur la landing page")
    print("=" * 60)

    try:
        response = requests.get("https://arkforge.fr/arkwatch.html", timeout=5)
        html = response.text

        # Vérifier la présence des éléments clés
        checks = {
            "CTA avec animation pulse": 'class="cta-button pulse"' in html,
            "Sticky CTA": 'class="sticky-cta"' in html,
            "Smooth scroll function": 'function smoothScroll' in html,
            "Trust badge": 'class="trust-badge"' in html,
            "USP sous le CTA": '✓ 3 URLs gratuites' in html,
        }

        all_ok = True
        for check, result in checks.items():
            status = "✓" if result else "❌"
            print(f"  {status} {check}")
            if not result:
                all_ok = False

        if all_ok:
            print("\n✅ Tous les éléments CTA sont présents")
            return True
        else:
            print("\n❌ Certains éléments CTA sont manquants")
            return False

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False


if __name__ == "__main__":
    print(f"\nTest démarré: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Test 1: Visibilité du CTA
    cta_ok = test_cta_visibility()

    # Test 2: Performance du parcours signup
    flow_ok = test_signup_flow_performance()

    # Résumé final
    print("\n" + "=" * 60)
    print("RÉSUMÉ FINAL")
    print("=" * 60)
    print(f"  {'✅' if cta_ok else '❌'} Visibilité du CTA")
    print(f"  {'✅' if flow_ok else '❌'} Performance signup flow (< 30s)")

    if cta_ok and flow_ok:
        print("\n✅ TOUS LES TESTS PASSÉS")
        exit(0)
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
        exit(1)
