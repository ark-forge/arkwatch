#!/usr/bin/env python3
"""
Health check for /free-trial page and conversion funnel.
Usage: python3 check_free_trial_health.py
Exit codes: 0=OK, 1=WARNING, 2=CRITICAL
"""

import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Configuration
BASE_URL = "https://arkforge.fr"
API_URL = "https://watch.arkforge.fr"
FREE_TRIAL_PAGE = f"{BASE_URL}/free-trial.html"
API_SPOTS = f"{API_URL}/api/free-trial/spots"
DASHBOARD_PAGE = f"{BASE_URL}/dashboard.html"
TIMEOUT = 10


def check_url(url: str, expected_status: int = 200) -> tuple[bool, str]:
    """Check if URL is accessible and returns expected status."""
    try:
        req = Request(url, headers={"User-Agent": "ArkWatch-HealthCheck/1.0"})
        with urlopen(req, timeout=TIMEOUT) as response:
            status = response.getcode()
            if status == expected_status:
                return True, f"OK ({status})"
            else:
                return False, f"Unexpected status: {status} (expected {expected_status})"
    except HTTPError as e:
        return False, f"HTTP Error: {e.code}"
    except URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_api_spots() -> tuple[bool, str]:
    """Check if API spots endpoint returns valid data."""
    try:
        req = Request(API_SPOTS, headers={"User-Agent": "ArkWatch-HealthCheck/1.0"})
        with urlopen(req, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode())
            required_keys = ["total", "taken", "remaining", "available"]
            if all(k in data for k in required_keys):
                return True, f"OK (remaining: {data['remaining']}/{data['total']})"
            else:
                return False, f"Missing keys in response: {data}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_page_content(url: str, required_content: list[str]) -> tuple[bool, str]:
    """Check if page contains required content."""
    try:
        req = Request(url, headers={"User-Agent": "ArkWatch-HealthCheck/1.0"})
        with urlopen(req, timeout=TIMEOUT) as response:
            content = response.read().decode()
            missing = [item for item in required_content if item not in content]
            if not missing:
                return True, "OK (all content present)"
            else:
                return False, f"Missing content: {', '.join(missing)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    print("=== Free Trial Health Check ===")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
    
    checks = []
    
    # Check 1: Free trial page accessible
    print("1. Checking /free-trial page...")
    ok, msg = check_url(FREE_TRIAL_PAGE)
    checks.append(("Free Trial Page", ok, msg))
    print(f"   {'✅' if ok else '❌'} {msg}")
    
    # Check 2: Page contains essential content
    print("2. Checking page content...")
    required = ["6 Months FREE", "api/early-signup", "dashboard.html"]
    ok, msg = check_page_content(FREE_TRIAL_PAGE, required)
    checks.append(("Page Content", ok, msg))
    print(f"   {'✅' if ok else '❌'} {msg}")
    
    # Check 3: API spots endpoint
    print("3. Checking API /api/free-trial/spots...")
    ok, msg = check_api_spots()
    checks.append(("API Spots", ok, msg))
    print(f"   {'✅' if ok else '❌'} {msg}")
    
    # Check 4: Dashboard accessible (redirect target)
    print("4. Checking dashboard page...")
    ok, msg = check_url(DASHBOARD_PAGE)
    checks.append(("Dashboard", ok, msg))
    print(f"   {'✅' if ok else '❌'} {msg}")
    
    # Summary
    print("\n=== Summary ===")
    total = len(checks)
    passed = sum(1 for _, ok, _ in checks if ok)
    failed = total - passed
    
    print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
    
    if failed == 0:
        print("✅ All checks passed - System healthy")
        return 0
    elif failed <= 1:
        print("⚠️  Some checks failed - System degraded")
        return 1
    else:
        print("❌ Multiple checks failed - System critical")
        return 2


if __name__ == "__main__":
    sys.exit(main())
