# Code Snippets - Optimisation /api/try
**Date**: 2026-02-09
**Fichier cible**: `/opt/claude-ceo/workspace/arkwatch/src/api/routers/try_check.py`
**Investigation**: Tâche #20260922

---

## PHASE 1: Timeouts Optimisés (30 min)

### Changement 1: Timeout HTTP (ligne 226)

**AVANT**:
```python
async with httpx.AsyncClient(
    timeout=15,
    follow_redirects=True,
    headers={
        "User-Agent": "ArkWatch/1.0 (Web Monitoring Service)",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    },
) as client:
```

**APRÈS**:
```python
async with httpx.AsyncClient(
    timeout=httpx.Timeout(8.0, connect=3.0, read=5.0),  # ← MODIFIÉ: 8s total, 3s connect, 5s read
    follow_redirects=True,
    headers={
        "User-Agent": "ArkWatch/1.0 (Web Monitoring Service)",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    },
) as client:
```

---

### Changement 2: Timeout SSL (ligne 66)

**AVANT**:
```python
with socket.create_connection((hostname, port), timeout=5) as sock:
```

**APRÈS**:
```python
with socket.create_connection((hostname, port), timeout=2) as sock:  # ← MODIFIÉ: 2s au lieu de 5s
```

---

### Changement 3: Timeout asyncio SSL (ligne 280)

**AVANT**:
```python
ssl_info = await asyncio.wait_for(ssl_future, timeout=8.0)
```

**APRÈS**:
```python
ssl_info = await asyncio.wait_for(ssl_future, timeout=3.0)  # ← MODIFIÉ: 3s au lieu de 8s
```

---

### Changement 4: Exception timeout (ligne 269-270)

**AVANT**:
```python
except httpx.TimeoutException:
    status = "down"
    latency_ms = 15000
```

**APRÈS**:
```python
except httpx.TimeoutException:
    status = "down"
    latency_ms = 8000  # ← MODIFIÉ: refléter nouveau timeout
```

---

### Changement 5: Timeout endpoint /check (ligne 149)

**AVANT**:
```python
async with httpx.AsyncClient(
    timeout=15,
    follow_redirects=True,
    ...
) as client:
```

**APRÈS**:
```python
async with httpx.AsyncClient(
    timeout=httpx.Timeout(8.0, connect=3.0, read=5.0),  # ← MODIFIÉ: cohérence avec /try
    follow_redirects=True,
    ...
) as client:
```

---

### Changement 6: Exception timeout /check (ligne 175-176)

**AVANT**:
```python
except httpx.TimeoutException:
    status = "down"
    latency_ms = 15000
```

**APRÈS**:
```python
except httpx.TimeoutException:
    status = "down"
    latency_ms = 8000  # ← MODIFIÉ: cohérence
```

---

## PHASE 2: Cache Redis (2-3h)

### Étape 1: Installation Redis

```bash
# Sur le serveur
sudo apt update
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Vérifier que Redis fonctionne
redis-cli ping
# Doit retourner: PONG

# Installer client Python
cd /opt/claude-ceo/workspace/arkwatch
pip install redis
```

---

### Étape 2: Import et configuration (début du fichier)

**AJOUTER après les imports existants (ligne 15)**:
```python
import redis
import hashlib

# Redis client for caching try results
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
except redis.ConnectionError:
    REDIS_AVAILABLE = False
    print("WARNING: Redis not available, caching disabled")

CACHE_TTL = 1800  # 30 minutes
```

---

### Étape 3: Fonction helper cache key

**AJOUTER après les imports (ligne 25)**:
```python
def _get_cache_key(url: str) -> str:
    """Generate Redis cache key for a URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return f"try:{url_hash}"
```

---

### Étape 4: Modifier endpoint /try (ligne 191-298)

**AJOUTER au début de try_check() (après rate limit check, ligne 198)**:
```python
@router.post("/try")
async def try_check(request_body: TryCheckRequest, request: Request):
    """
    Try-before-signup: instant health check of any URL.
    Returns status, latency, SSL info — no account needed.
    """
    ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")
    _check_rate_limit(ip)

    url = str(request_body.url)

    # ← AJOUTER ICI: Check cache first
    if REDIS_AVAILABLE:
        try:
            cache_key = _get_cache_key(url)
            cached = redis_client.get(cache_key)
            if cached:
                import json
                return TryCheckResponse(**json.loads(cached))
        except redis.ConnectionError:
            pass  # Fallback: continue without cache
    # FIN AJOUT

    # SSRF protection (ligne 202 originale continue ici)
    safe, reason, _ = _is_safe_url(url)
    ...
```

---

### Étape 5: Stocker en cache avant return (ligne 284-298)

**REMPLACER le return final (ligne 284-298)**:

**AVANT**:
```python
    return TryCheckResponse(
        url=url,
        status=status,
        status_code=status_code,
        latency_ms=latency_ms,
        title=title,
        ssl=ssl_info,
        server=server,
        checked_at=datetime.now(timezone.utc).isoformat(),
        cta={
            "message": "Get alerts when this goes down — create free account",
            "url": f"https://arkforge.fr/register.html?monitor={hostname}",
            "label": "Start Monitoring Free",
        },
    )
```

**APRÈS**:
```python
    result = TryCheckResponse(
        url=url,
        status=status,
        status_code=status_code,
        latency_ms=latency_ms,
        title=title,
        ssl=ssl_info,
        server=server,
        checked_at=datetime.now(timezone.utc).isoformat(),
        cta={
            "message": "Get alerts when this goes down — create free account",
            "url": f"https://arkforge.fr/register.html?monitor={hostname}",
            "label": "Start Monitoring Free",
        },
    )

    # Store in cache before returning
    if REDIS_AVAILABLE:
        try:
            cache_key = _get_cache_key(url)
            import json
            redis_client.setex(cache_key, CACHE_TTL, result.json())
        except redis.ConnectionError:
            pass  # Fail silently if Redis unavailable

    return result
```

---

## PHASE 3: Parsing HTML Optimisé (1h)

### Changement: Regex au lieu de find() (ligne 255-264)

**AJOUTER import en haut du fichier**:
```python
import re
```

**AVANT**:
```python
# Extract title from HTML
content_type = response.headers.get("content-type", "")
if "html" in content_type:
    text = response.text[:10000]  # limit parsing
    start_tag = text.lower().find("<title")
    if start_tag != -1:
        end_open = text.find(">", start_tag)
        end_tag = text.lower().find("</title>", end_open)
        if end_open != -1 and end_tag != -1:
            title = text[end_open + 1:end_tag].strip()[:200]
```

**APRÈS**:
```python
# Extract title from HTML
content_type = response.headers.get("content-type", "")
if "html" in content_type:
    text = response.text[:10000]  # limit parsing
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', text, re.IGNORECASE)
    title = title_match.group(1).strip()[:200] if title_match else None
```

---

## TESTS VALIDATION

### Test Phase 1 (Timeouts)

```bash
# Test 1: Site rapide (doit être <500ms)
time curl -X POST https://watch.arkforge.fr/api/try \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'

# Test 2: Site lent simulé (doit timeout à 8s, pas 15s)
time curl -X POST https://watch.arkforge.fr/api/try \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpstat.us/200?sleep=10000"}'
# Doit retourner en ~8s avec status="down"
```

---

### Test Phase 2 (Cache Redis)

```bash
# Test 1: Premier appel (cache miss, devrait être ~600ms)
time curl -X POST https://watch.arkforge.fr/api/try \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test 2: Deuxième appel immédiat (cache hit, doit être <150ms)
time curl -X POST https://watch.arkforge.fr/api/try \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Vérifier cache Redis
redis-cli KEYS "try:*"
redis-cli GET "try:5d41402abc4b2a76b9719d911017c592"  # hash MD5 de l'URL
```

---

### Test Phase 3 (Parsing)

```bash
# Test avec site ayant title complexe
curl -X POST https://watch.arkforge.fr/api/try \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com"}' | jq '.title'

# Doit extraire correctement: "GitHub: Let's build from here..."
```

---

## MONITORING POST-DÉPLOIEMENT

### Vérifier performance

```bash
# Logs API temps réel
tail -f /var/log/arkwatch/api.log | grep "POST /api/try"

# Stats Redis
redis-cli INFO stats | grep hits
redis-cli DBSIZE  # Nombre de clés en cache
```

---

### Dashboard métriques (optionnel)

```python
# Ajouter endpoint /api/cache-stats (debug only)
@router.get("/cache-stats")
async def cache_stats():
    if not REDIS_AVAILABLE:
        return {"available": False}

    info = redis_client.info("stats")
    return {
        "available": True,
        "keys": redis_client.dbsize(),
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
    }
```

---

## ROLLBACK SI PROBLÈME

### Phase 1 (Timeouts)
```bash
# Restaurer anciens timeouts:
# timeout=15 au lieu de timeout=httpx.Timeout(8.0, ...)
# timeout=5 au lieu de timeout=2 (SSL)
# timeout=8.0 au lieu de timeout=3.0 (asyncio)
```

### Phase 2 (Cache)
```bash
# Désactiver cache sans redémarrer
redis-cli FLUSHDB  # Vider cache
# Ou: Mettre REDIS_AVAILABLE = False temporairement
```

---

**NOTES**:
- Toujours tester sur environnement de dev AVANT production
- Backup try_check.py avant modifications
- Vérifier logs après déploiement (premiers 30min critiques)
- Monitorer taux erreur et latence P95
