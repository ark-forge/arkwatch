#!/usr/bin/env python3
"""
Test de performance API ArkWatch
Mesure les temps de réponse de tous les endpoints critiques
"""

import asyncio
import time
from typing import Any

import httpx


API_BASE_URL = "https://watch.arkforge.fr"
TIMEOUT = 10.0


async def measure_endpoint(
    client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
) -> dict:
    """Mesure le temps de réponse d'un endpoint"""
    start = time.perf_counter()
    try:
        response = await client.request(method, f"{API_BASE_URL}{path}", **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "path": path,
            "method": method,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "success": 200 <= response.status_code < 400,
        }
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "path": path,
            "method": method,
            "status": 0,
            "duration_ms": round(duration_ms, 2),
            "success": False,
            "error": str(e),
        }


async def run_performance_tests() -> dict:
    """Exécute tous les tests de performance"""
    endpoints = [
        # Health check
        ("GET", "/health"),
        # Public endpoints
        ("GET", "/"),
        ("GET", "/api/pricing"),
        # Try before signup (public, important pour conversion)
        ("POST", "/api/try", {"json": {"url": "https://example.com"}}),
        # Auth endpoints (important pour onboarding)
        ("POST", "/api/auth/signup", {"json": {"email": "test@example.com"}}),
        # Stats (public, important pour transparence)
        ("GET", "/api/stats"),
        # Lead analytics (public)
        ("GET", "/api/leadgen/analytics"),
    ]

    results = []
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        for method, path, *args in endpoints:
            kwargs = args[0] if args else {}
            result = await measure_endpoint(client, method, path, **kwargs)
            results.append(result)
            # Pause entre requêtes pour ne pas surcharger
            await asyncio.sleep(0.2)

    return analyze_results(results)


def analyze_results(results: list[dict]) -> dict:
    """Analyse les résultats et génère un rapport"""
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    slow = [r for r in successful if r["duration_ms"] > 500]

    durations = [r["duration_ms"] for r in successful]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_endpoints": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "slow_endpoints": len(slow),
        "avg_duration_ms": round(avg_duration, 2),
        "max_duration_ms": round(max(durations), 2) if durations else 0,
        "min_duration_ms": round(min(durations), 2) if durations else 0,
        "results": results,
        "slow_endpoints_detail": slow,
        "failed_endpoints_detail": failed,
    }


def print_report(analysis: dict) -> None:
    """Affiche le rapport de performance"""
    print("=" * 70)
    print("RAPPORT DE PERFORMANCE API ARKWATCH")
    print("=" * 70)
    print(f"Timestamp: {analysis['timestamp']}")
    print(f"Endpoints testés: {analysis['total_endpoints']}")
    print(f"Succès: {analysis['successful']} | Échecs: {analysis['failed']}")
    print(f"Durée moyenne: {analysis['avg_duration_ms']}ms")
    print(f"Durée min: {analysis['min_duration_ms']}ms")
    print(f"Durée max: {analysis['max_duration_ms']}ms")
    print()

    if analysis["slow_endpoints"]:
        print("⚠️  ENDPOINTS LENTS (>500ms):")
        print("-" * 70)
        for endpoint in analysis["slow_endpoints_detail"]:
            print(
                f"  {endpoint['method']:6} {endpoint['path']:40} "
                f"{endpoint['duration_ms']:>7.2f}ms [HTTP {endpoint['status']}]"
            )
        print()

    if analysis["failed_endpoints_detail"]:
        print("❌ ENDPOINTS EN ÉCHEC:")
        print("-" * 70)
        for endpoint in analysis["failed_endpoints_detail"]:
            error = endpoint.get("error", "Unknown error")
            print(f"  {endpoint['method']:6} {endpoint['path']:40}")
            print(f"    → Erreur: {error}")
        print()

    print("DÉTAIL DE TOUS LES ENDPOINTS:")
    print("-" * 70)
    for result in sorted(analysis["results"], key=lambda x: x["duration_ms"], reverse=True):
        status_emoji = "✅" if result["success"] else "❌"
        speed_emoji = "🐌" if result["duration_ms"] > 500 else "⚡"
        print(
            f"{status_emoji} {speed_emoji} {result['method']:6} {result['path']:35} "
            f"{result['duration_ms']:>7.2f}ms [HTTP {result['status']}]"
        )

    print("=" * 70)

    # Recommandations
    print("\nRECOMMANDATIONS:")
    if analysis["avg_duration_ms"] < 300:
        print("✅ Performance excellente (moyenne < 300ms)")
    elif analysis["avg_duration_ms"] < 500:
        print("✅ Performance bonne (moyenne < 500ms)")
    else:
        print("⚠️  Performance à améliorer (moyenne > 500ms)")

    if analysis["slow_endpoints"]:
        print(f"⚠️  {len(analysis['slow_endpoints_detail'])} endpoint(s) lent(s) à optimiser")
        print("   Suggestions:")
        print("   - Ajouter du caching pour les endpoints publics fréquents")
        print("   - Optimiser les requêtes DB (index, N+1 queries)")
        print("   - Utiliser async/await pour les opérations I/O")

    if analysis["failed_endpoints_detail"]:
        print(f"❌ {len(analysis['failed_endpoints_detail'])} endpoint(s) en erreur - CRITIQUE")

    print()


async def main():
    print("Démarrage des tests de performance API ArkWatch...")
    print(f"URL de base: {API_BASE_URL}")
    print()

    analysis = await run_performance_tests()
    print_report(analysis)

    # Retour 0 si objectif atteint (<500ms moyenne), 1 sinon
    return 0 if analysis["avg_duration_ms"] < 500 and analysis["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
