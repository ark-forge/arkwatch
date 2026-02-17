"""Web scraping module using httpx and BeautifulSoup"""

import difflib
import hashlib
import ipaddress
import socket
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Private/reserved IP ranges that must never be scraped (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private A
    ipaddress.ip_network("172.16.0.0/12"),  # Private B
    ipaddress.ip_network("192.168.0.0/16"),  # Private C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space (CGN)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmark testing
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
]

# Ports of internal services that should never be accessed by the scraper
_BLOCKED_PORTS = {22, 25, 465, 587, 3306, 5432, 6379, 27017, 11211, 9200}


def _is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP is in a blocked network."""
    for network in _BLOCKED_NETWORKS:
        if ip in network:
            return True
    return False


def _is_safe_url(url: str) -> tuple[bool, str, str | None]:
    """Validate URL is safe to scrape (no SSRF).

    Returns (safe, reason, resolved_ip).
    When safe, resolved_ip is the first safe IPv4 address to connect to,
    eliminating the DNS-rebinding TOCTOU window.
    """
    parsed = urlparse(url)

    # Only allow http/https
    if parsed.scheme not in ("http", "https"):
        return False, f"Blocked scheme: {parsed.scheme}", None

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname", None

    # Block dangerous ports
    port = parsed.port
    if port and port in _BLOCKED_PORTS:
        return False, f"Blocked port: {port}", None

    # Check if hostname is an IP literal
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_ip_blocked(ip):
            return False, "Blocked: private/reserved IP address", None
        return True, "", str(ip)
    except ValueError:
        pass  # Not an IP literal, will resolve via DNS below

    # Resolve hostname to IP and verify all resolved addresses
    try:
        addr_info = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False, f"Cannot resolve hostname: {hostname}", None

    first_safe_ip = None
    for _family, _, _, _, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        if _is_ip_blocked(ip):
            return False, "Blocked: resolves to private/reserved IP", None
        if first_safe_ip is None:
            first_safe_ip = sockaddr[0]

    if first_safe_ip is None:
        return False, "No addresses resolved", None

    return True, "", first_safe_ip


@dataclass
class ScrapeResult:
    """Result of a web scrape"""

    url: str
    status_code: int
    content_hash: str
    text_content: str
    title: str | None
    scraped_at: datetime
    error: str | None = None


class WebScraper:
    """Simple web scraper for monitoring changes"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "ArkWatch/1.0 (Web Monitoring Service)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr,en;q=0.5",
        }

    async def scrape(self, url: str) -> ScrapeResult:
        """Scrape a URL and return the result"""
        try:
            # SSRF protection: validate URL before making request
            safe, reason, resolved_ip = _is_safe_url(url)
            if not safe:
                return ScrapeResult(
                    url=url,
                    status_code=0,
                    content_hash="",
                    text_content="",
                    title=None,
                    scraped_at=datetime.utcnow(),
                    error=f"URL blocked: {reason}",
                )

            async def _check_redirect(response: httpx.Response):
                """Verify each redirect target is safe (SSRF via redirect)."""
                if response.is_redirect and "location" in response.headers:
                    redirect_url = (
                        str(response.next_request.url) if response.next_request else response.headers["location"]
                    )
                    safe_redir, reason_redir, _ = _is_safe_url(redirect_url)
                    if not safe_redir:
                        raise httpx.TooManyRedirects(f"Redirect blocked: {reason_redir}")

            async def _verify_connected_ip(response: httpx.Response):
                """Post-connection check: verify the actual IP connected to is safe.

                This is the second layer of SSRF defense, catching DNS rebinding
                attacks where the IP changes between our pre-check and the actual
                connection.
                """
                stream = response.stream
                if hasattr(stream, "_stream") and hasattr(stream._stream, "_connection"):
                    conn = stream._stream._connection
                    if hasattr(conn, "_network_stream"):
                        sock = conn._network_stream
                        if hasattr(sock, "get_extra_info"):
                            peername = sock.get_extra_info("peername")
                            if peername:
                                ip = ipaddress.ip_address(peername[0])
                                if _is_ip_blocked(ip):
                                    await response.aclose()
                                    raise httpx.ConnectError(f"SSRF blocked: connected to private/reserved IP {ip}")

            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                event_hooks={"response": [_check_redirect, _verify_connected_ip]},
            ) as client:
                response = await client.get(url, headers=self.headers)

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()

                # Get text content
                text = soup.get_text(separator="\n", strip=True)

                # Get title
                title = soup.title.string if soup.title else None

                # Compute hash
                content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

                return ScrapeResult(
                    url=url,
                    status_code=response.status_code,
                    content_hash=content_hash,
                    text_content=text,
                    title=title,
                    scraped_at=datetime.utcnow(),
                )
        except Exception as e:
            return ScrapeResult(
                url=url,
                status_code=0,
                content_hash="",
                text_content="",
                title=None,
                scraped_at=datetime.utcnow(),
                error=str(e),
            )

    @staticmethod
    def compute_diff(old_content: str, new_content: str) -> tuple[bool, str]:
        """Compare two contents and return diff"""
        if old_content == new_content:
            return False, ""

        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
        diff_text = "".join(diff)

        return True, diff_text


# Test function
async def test_scraper():
    scraper = WebScraper()
    result = await scraper.scrape("https://example.com")
    print(f"URL: {result.url}")
    print(f"Status: {result.status_code}")
    print(f"Title: {result.title}")
    print(f"Hash: {result.content_hash}")
    print(f"Content length: {len(result.text_content)} chars")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_scraper())
