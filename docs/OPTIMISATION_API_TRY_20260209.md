# Optimisation Endpoint `/api/try` - Analyse Technique
**Date**: 2026-02-09
**Endpoint**: POST /api/try
**Performance actuelle**: 980ms
**Objectif**: <500ms (idéalement <300ms)

## Analyse du Code

### Opérations Coûteuses Identifiées

```python
# Ligne 225-235: Requête HTTP vers URL externe (PRINCIPALE CAUSE)
async with httpx.AsyncClient(timeout=15, ...) as client:
    response = await client.get(url)  # ← 800-900ms en moyenne
```

**Problème**: Dépend entièrement de la latence du site cible.

```python
# Ligne 215: Check SSL synchrone (convertie en thread)
ssl_future = asyncio.to_thread(_get_ssl_info, hostname, port)  # ← 50-100ms
```

**Problème**: Timeout SSL à 5s (ligne 66), peut bloquer longtemps.

```python
# Ligne 258-264: Parsing HTML pour extraire <title>
text = response.text[:10000]  # ← 20-50ms pour gros HTML
```

**Problème**: Parsing manuel de HTML, pas optimisé.

## Solutions Recommandées (par ordre de priorité)

### 🔴 PRIORITÉ 1: Cache Redis (Gain estimé: 80-90%)

**Impact**: Réduire 980ms → 100-150ms pour URLs déjà testées

**Implémentation**:
```python
import redis
import hashlib

redis_client = redis.Redis(host='localhost', port=6379, db=0)
CACHE_TTL = 1800  # 30 minutes

def _get_cache_key(url: str) -> str:
    return f"try:{hashlib.md5(url.encode()).hexdigest()}"

@router.post("/try")
async def try_check(request_body: TryCheckRequest, request: Request):
    url = str(request_body.url)
    cache_key = _get_cache_key(url)

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return TryCheckResponse.parse_raw(cached)

    # ... existing check logic ...

    # Store in cache
    response_json = result.json()
    redis_client.setex(cache_key, CACHE_TTL, response_json)
    return result
```

**Avantages**:
- Réponse instantanée pour URLs populaires
- Réduit charge serveur
- TTL court (30min) = données fraîches

**Installation**: `pip install redis` + service Redis

---

### 🟡 PRIORITÉ 2: Timeout plus agressif (Gain estimé: 30-40%)

**Impact**: Éviter attentes >5s sur sites lents

**Implémentation**:
```python
# Ligne 226: Réduire timeout de 15s → 8s
async with httpx.AsyncClient(
    timeout=httpx.Timeout(8.0, connect=3.0, read=5.0),  # ← 8s total, 3s connect, 5s read
    follow_redirects=True,
    ...
) as client:
```

**Avantages**:
- Réponse max 8s au lieu de 15s
- Améliore UX (feedback rapide)
- Sites lents marqués "down" rapidement

---

### 🟡 PRIORITÉ 3: Optimiser SSL Check (Gain estimé: 20%)

**Impact**: Réduire 50-100ms → 20-30ms

**Implémentation**:
```python
# Ligne 66: Timeout SSL plus court
with socket.create_connection((hostname, port), timeout=2) as sock:  # ← 2s au lieu de 5s
```

**Avantages**:
- SSL check plus rapide
- Timeout cohérent avec HTTP timeout

---

### 🟢 PRIORITÉ 4: Optimiser parsing HTML (Gain estimé: 10%)

**Impact**: Réduire 20-50ms → 5-10ms

**Implémentation**:
```python
# Option 1: Regex simple (plus rapide que find manuel)
import re
title_match = re.search(r'<title[^>]*>([^<]+)</title>', text[:10000], re.IGNORECASE)
title = title_match.group(1).strip()[:200] if title_match else None

# Option 2: Limiter taille téléchargée (économise aussi bande passante)
# Ligne 258: Lire seulement premiers KB
async with httpx.AsyncClient(...) as client:
    async with client.stream("GET", url) as response:
        chunks = []
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            if sum(len(c) for c in chunks) > 50000:  # Stop at 50KB
                break
        content = b"".join(chunks)
```

**Avantages**:
- Parsing plus rapide
- Économie bande passante
- Moins de mémoire utilisée

---

### 🟢 PRIORITÉ 5: Response streaming (Gain UX: énorme)

**Impact**: Feedback immédiat utilisateur

**Implémentation** (architecture avancée):
```python
from fastapi.responses import StreamingResponse

@router.post("/try")
async def try_check(request_body: TryCheckRequest, request: Request):
    async def generate():
        # Envoyer immédiatement réponse partielle
        yield json.dumps({"status": "checking", "url": url}) + "\n"

        # Faire check HTTP
        result = await _do_http_check(url)
        yield json.dumps({"status": "partial", "http": result}) + "\n"

        # Faire check SSL
        ssl_result = await _do_ssl_check(url)
        yield json.dumps({"status": "complete", "http": result, "ssl": ssl_result}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

**Avantages**:
- UX améliorée (feedback progressif)
- Utilisateur voit résultat HTTP immédiatement
- SSL peut arriver après sans bloquer

---

## Plan d'Implémentation Recommandé

### Phase 1: Quick Wins (1-2h)
1. ✅ Réduire timeout HTTP (15s → 8s)
2. ✅ Réduire timeout SSL (5s → 2s)
3. ✅ Optimiser parsing HTML (regex)

**Gain estimé**: 980ms → 600-700ms

### Phase 2: Cache Redis (2-3h)
1. ✅ Installer Redis sur serveur
2. ✅ Implémenter cache avec TTL 30min
3. ✅ Tester invalidation cache

**Gain estimé**: 600ms → 100-150ms (pour hits)

### Phase 3: Optimisations avancées (optionnel, 4-6h)
1. Streaming response
2. Pre-fetch populaires URLs
3. CDN pour API (Cloudflare Workers)

**Gain estimé**: <100ms perçu

---

## Benchmark Cible Post-Optimisation

| Scénario | Avant | Après (Phase 1) | Après (Phase 2) | Objectif |
|----------|-------|-----------------|-----------------|----------|
| Cache HIT | 980ms | 980ms | **100ms** | ✅ <500ms |
| Cache MISS - Site rapide | 980ms | **400ms** | 400ms | ✅ <500ms |
| Cache MISS - Site lent | 980ms | **700ms** | 700ms | ⚠️ Acceptable |
| Cache MISS - Site down | 15000ms | **8000ms** | 8000ms | ✅ Timeout rapide |

---

## Tests de Validation

```bash
# Test 1: Mesurer avant optimisation
curl -w "@curl-format.txt" -X POST https://watch.arkforge.fr/api/try \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test 2: Mesurer après Phase 1
# (répéter commande)

# Test 3: Mesurer cache hit (Phase 2)
# (répéter 2x même URL, 2ème doit être <150ms)

# Test 4: Load test
ab -n 100 -c 10 -p request.json -T application/json https://watch.arkforge.fr/api/try
```

**Fichier curl-format.txt**:
```
time_total: %{time_total}s
time_connect: %{time_connect}s
time_starttransfer: %{time_starttransfer}s
```

---

## Risques & Mitigations

### Risque 1: Cache stale data
- **Mitigation**: TTL court (30min)
- **Monitoring**: Logger cache hit rate

### Risque 2: Redis down
- **Mitigation**: Fallback graceful (ignorer cache si erreur)
```python
try:
    cached = redis_client.get(cache_key)
except redis.ConnectionError:
    cached = None  # Fallback: skip cache
```

### Risque 3: Timeout trop court
- **Mitigation**: Différencier timeout/error dans réponse
- **UX**: "Site took >8s, marked as slow" vs "Site unreachable"

---

## Conclusion

**Effort estimé**: 3-5h (Phases 1+2)
**Gain attendu**: 980ms → 100-400ms (60-90% amélioration)
**ROI**: TRÈS ÉLEVÉ (endpoint critique conversion)

**Recommandation CEO**: Implémenter Phases 1+2 immédiatement (priorité P1).
