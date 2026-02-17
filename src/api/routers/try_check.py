"""Try-before-signup endpoint - instant URL health check without account"""

import asyncio
import ssl
import socket
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from ...scraper.scraper import _is_safe_url

router = APIRouter()

# Rate limiting: max 10 checks per IP per 15 minutes
_try_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 900  # 15 minutes
_RATE_LIMIT_MAX = 10


def _check_rate_limit(ip: str):
    now = time.time()
    _try_attempts[ip] = [t for t in _try_attempts[ip] if now - t < _RATE_LIMIT_WINDOW]
    if len(_try_attempts[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many checks. Please wait a few minutes or create a free account for unlimited checks."
        )
    _try_attempts[ip].append(now)


class TryCheckRequest(BaseModel):
    url: HttpUrl


class SSLInfo(BaseModel):
    valid: bool
    issuer: str | None = None
    subject: str | None = None
    expires: str | None = None
    days_remaining: int | None = None
    protocol: str | None = None
    error: str | None = None


class TryCheckResponse(BaseModel):
    url: str
    status: str  # "up", "down", "degraded", "error"
    status_code: int | None = None
    latency_ms: int
    title: str | None = None
    ssl: SSLInfo | None = None
    server: str | None = None
    checked_at: str
    cta: dict


def _get_ssl_info(hostname: str, port: int = 443) -> SSLInfo:
    """Get SSL certificate details for a hostname."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                protocol = ssock.version()

                # Parse issuer
                issuer_parts = []
                for rdn in cert.get("issuer", ()):
                    for attr_type, attr_value in rdn:
                        if attr_type in ("organizationName", "commonName"):
                            issuer_parts.append(attr_value)
                issuer = ", ".join(issuer_parts) if issuer_parts else None

                # Parse subject CN
                subject = None
                for rdn in cert.get("subject", ()):
                    for attr_type, attr_value in rdn:
                        if attr_type == "commonName":
                            subject = attr_value
                            break

                # Parse expiry
                not_after = cert.get("notAfter")
                expires = None
                days_remaining = None
                if not_after:
                    expiry_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    expires = expiry_dt.isoformat()
                    days_remaining = (expiry_dt - datetime.now(timezone.utc)).days

                return SSLInfo(
                    valid=True,
                    issuer=issuer,
                    subject=subject,
                    expires=expires,
                    days_remaining=days_remaining,
                    protocol=protocol,
                )
    except ssl.SSLCertVerificationError as e:
        return SSLInfo(valid=False, error=f"Certificate invalid: {e.verify_message}")
    except ssl.SSLError as e:
        return SSLInfo(valid=False, error=f"SSL error: {str(e)}")
    except (socket.timeout, socket.gaierror, OSError):
        return SSLInfo(valid=False, error="Could not establish SSL connection")


class CheckResponse(BaseModel):
    status: str
    status_code: int | None = None
    response_time_ms: int
    timestamp: str
    url: str


@router.get("/check")
async def check_url(request: Request, url: str | None = None):
    """
    Public GET endpoint: check any URL status.
    Usage: GET /api/check?url=example.com
    Returns {status, status_code, response_time_ms, timestamp, url} — no account needed.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' query parameter. Usage: /api/check?url=example.com")

    ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")
    _check_rate_limit(ip)

    # Auto-add https:// if no scheme provided
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # SSRF protection
    safe, reason, _ = _is_safe_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"URL not allowed: {reason}")

    status = "error"
    status_code = None
    latency_ms = 0

    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": "ArkWatch/1.0 (Web Monitoring Service)",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
        ) as client:
            start = time.monotonic()
            response = await client.get(url)
            latency_ms = int((time.monotonic() - start) * 1000)

            status_code = response.status_code

            if 200 <= status_code < 400:
                status = "up"
            elif status_code == 502 or status_code == 503:
                status = "down"
            elif 400 <= status_code < 500:
                status = "degraded"
            elif status_code >= 500:
                status = "down"

            if status == "up" and latency_ms > 3000:
                status = "degraded"

    except httpx.TimeoutException:
        status = "down"
        latency_ms = 15000
    except httpx.ConnectError:
        status = "down"
    except Exception:
        status = "error"

    return CheckResponse(
        status=status,
        status_code=status_code,
        response_time_ms=latency_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
        url=url,
    )


@router.post("/try")
async def try_check(request_body: TryCheckRequest, request: Request):
    """
    Try-before-signup: instant health check of any URL.
    Returns status, latency, SSL info — no account needed.
    """
    ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")
    _check_rate_limit(ip)

    url = str(request_body.url)

    # SSRF protection
    safe, reason, _ = _is_safe_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"URL not allowed: {reason}")

    parsed = urlparse(url)
    hostname = parsed.hostname
    is_https = parsed.scheme == "https"

    # Run HTTP check and SSL check concurrently
    ssl_future = None
    if is_https and hostname:
        port = parsed.port or 443
        ssl_future = asyncio.to_thread(_get_ssl_info, hostname, port)

    # HTTP health check with latency measurement
    status = "error"
    status_code = None
    latency_ms = 0
    title = None
    server = None

    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": "ArkWatch/1.0 (Web Monitoring Service)",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
        ) as client:
            start = time.monotonic()
            response = await client.get(url)
            latency_ms = int((time.monotonic() - start) * 1000)

            status_code = response.status_code

            # Determine status
            if 200 <= status_code < 300:
                status = "up"
            elif 300 <= status_code < 400:
                status = "up"  # redirects resolved by follow_redirects
            elif status_code == 503 or status_code == 502:
                status = "down"
            elif 400 <= status_code < 500:
                status = "degraded"
            elif status_code >= 500:
                status = "down"

            # Latency-based degradation
            if status == "up" and latency_ms > 3000:
                status = "degraded"

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

            server = response.headers.get("server")

    except httpx.TimeoutException:
        status = "down"
        latency_ms = 15000
    except httpx.ConnectError:
        status = "down"
    except Exception:
        status = "error"

    # Await SSL result
    ssl_info = None
    if ssl_future:
        try:
            ssl_info = await asyncio.wait_for(ssl_future, timeout=8.0)
        except (asyncio.TimeoutError, Exception):
            ssl_info = SSLInfo(valid=False, error="SSL check timed out")

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
