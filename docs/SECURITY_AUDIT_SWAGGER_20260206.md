# Security Audit: Swagger/OpenAPI Exposure - TASK 20260288

## Status: ✅ SECURED

### 1. FastAPI Configuration (src/api/main.py:16-18)
- **Status**: ✅ Correctly configured for production
- **Details**:
  - `docs_url` set to `None` when `ARKWATCH_ENV != "development"`
  - `redoc_url` set to `None` when `ARKWATCH_ENV != "development"`
  - `openapi_url` set to `None` when `ARKWATCH_ENV != "development"`
- **Environment**: `ARKWATCH_ENV` not set in production (defaults to "production")
- **Result**: All FastAPI docs endpoints return 404

### 2. Nginx Defense-in-Depth Configuration (/etc/nginx/sites-enabled/arkwatch:122-125)
- **Status**: ✅ Additional layer of protection configured
- **Details**:
  ```nginx
  # API docs blocked in production (defense in depth)
  location = /docs { return 301 https://arkforge.fr/api-docs.html; }
  location = /openapi.json { return 404; }
  location = /redoc { return 404; }
  ```
- **Result**: Even if FastAPI was misconfigured, nginx blocks access

### 3. Testing Results

#### Direct FastAPI access (localhost:8080)
```
GET /docs → 404 Not Found
GET /redoc → 404 Not Found
GET /openapi.json → 404 Not Found
```

#### Via Nginx proxy (production)
```
GET /docs → 301 Redirect to https://arkforge.fr/api-docs.html
GET /redoc → 404 Not Found
GET /openapi.json → 404 Not Found
```

### 4. Security Assessment

**Before**:
- ❌ Swagger documentation was publicly accessible
- ❌ OpenAPI schema exposed API structure
- ❌ Redoc documentation available
- ❌ Information disclosure vulnerability (OWASP A09:2021)

**After**:
- ✅ FastAPI docs disabled in production code
- ✅ Nginx blocks direct access to /docs, /redoc, /openapi.json
- ✅ /docs redirects to static documentation page (controlled content)
- ✅ Defense in depth (two layers of protection)
- ✅ No information disclosure from live API

### 5. Configuration Details

**FastAPI (main.py)**:
```python
is_dev = os.getenv("ARKWATCH_ENV", "production") == "development"
app = FastAPI(
    title="ArkWatch API",
    description="Web monitoring API with AI-powered change summaries. Free tier: 3 URLs, daily checks.",
    version="0.1.0",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
    openapi_url="/openapi.json" if is_dev else None,
)
```

**Nginx Rules**:
1. `/docs` → 301 redirect (controlled documentation page)
2. `/openapi.json` → 404 (API schema not exposed)
3. `/redoc` → 404 (ReDoc UI not available)

### 6. Recommendations for Future

1. ✅ Static API documentation at arkforge.fr/api-docs.html (recommended, already implemented)
2. ✅ Nginx blocks all variants (already implemented)
3. Consider rate limiting on 404 responses (already implemented with `api_general` zone)
4. Consider logging suspicious requests to /docs, /redoc, /openapi.json (recommended for SOC)

### 7. Conclusion

**FAILLE CORRIGÉE**: The API documentation endpoints are properly secured in production with:
- Disabled in FastAPI when not in development mode
- Blocked by nginx with 404/301 responses
- Defense-in-depth approach protects against misconfiguration

**Risk Level**: MITIGATED (Low risk for this specific vector)

---

**Audit Date**: 2026-02-06
**Auditor**: Worker Fondations
**Task ID**: 20260288
