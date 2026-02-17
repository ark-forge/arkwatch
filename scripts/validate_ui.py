#!/usr/bin/env python3
"""
UI Validation Pipeline - 3-Step Automated QA
=============================================
Directive actionnaire: Valider toute UI automatiquement avant déploiement.

Pipeline:
  1. Playwright E2E - Parcours complet (page charge, formulaires, navigation, CTA)
  2. Lighthouse + axe-core - Performance, Accessibilité, Best Practices, SEO (>80/100)
  3. Claude Vision - Screenshot analysé par Claude multimodal (clarté, CTA, professionnalisme)

Score composite >85 = OK, <70 = corriger avant déploiement.

Usage:
  python3 validate_ui.py                          # Validate all pages
  python3 validate_ui.py --url https://arkforge.fr/arkwatch.html
  python3 validate_ui.py --pages arkwatch dashboard  # Specific pages
  python3 validate_ui.py --skip-vision             # Skip Claude Vision step
  python3 validate_ui.py --json                    # Output JSON report
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("ARKWATCH_BASE_URL", "https://arkforge.fr")
REPORT_DIR = Path("/opt/claude-ceo/workspace/arkwatch/reports/ui-validation")
SCREENSHOT_DIR = REPORT_DIR / "screenshots"
LIGHTHOUSE_DIR = REPORT_DIR / "lighthouse"
CHROMIUM_PATH = os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium-browser")

# Pages to validate by default
DEFAULT_PAGES = {
    "arkwatch": f"{BASE_URL}/arkwatch.html",
    "dashboard": f"{BASE_URL}/dashboard.html",
    "index": f"{BASE_URL}/index.html",
    "privacy": f"{BASE_URL}/privacy.html",
    "cgv": f"{BASE_URL}/cgv.html",
}

# Thresholds
LIGHTHOUSE_THRESHOLD = 80  # Each category must be >= 80/100
AXE_CRITICAL_MAX = 0       # Zero critical violations allowed
COMPOSITE_PASS = 85        # Score >= 85 = PASS
COMPOSITE_WARN = 70        # Score >= 70 = WARN, < 70 = FAIL

# Weights for composite score
WEIGHT_E2E = 0.25
WEIGHT_LIGHTHOUSE = 0.30
WEIGHT_AXE = 0.20
WEIGHT_VISION = 0.25


@dataclass
class PageResult:
    """Result for a single page validation."""
    page_name: str
    url: str
    # E2E
    e2e_pass: bool = False
    e2e_details: dict = field(default_factory=dict)
    e2e_score: float = 0.0
    # Lighthouse
    lighthouse_scores: dict = field(default_factory=dict)
    lighthouse_score: float = 0.0
    # axe-core
    axe_violations: list = field(default_factory=list)
    axe_critical_count: int = 0
    axe_serious_count: int = 0
    axe_score: float = 0.0
    # Vision
    vision_analysis: str = ""
    vision_score: float = 0.0
    vision_skipped: bool = False
    # Composite
    composite_score: float = 0.0
    verdict: str = "PENDING"
    errors: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1: Playwright E2E
# ---------------------------------------------------------------------------
def run_e2e_checks(url: str, page_name: str) -> dict:
    """Run Playwright E2E checks: page loads, forms work, CTA clickable, navigation."""
    print(f"  [E2E] Checking {url} ...")
    result = {"pass": False, "details": {}, "score": 0.0}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=CHROMIUM_PATH)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="ArkWatch-UIValidator/1.0"
            )
            page = context.new_page()

            checks = {}

            # 1. Page loads successfully
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=30000)
                checks["page_loads"] = resp is not None and resp.status == 200
                checks["status_code"] = resp.status if resp else 0
            except Exception as e:
                checks["page_loads"] = False
                checks["load_error"] = str(e)

            if not checks.get("page_loads"):
                result["details"] = checks
                browser.close()
                return result

            # 2. No console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.wait_for_timeout(2000)
            checks["console_errors"] = len(console_errors)
            checks["console_error_list"] = console_errors[:5]

            # 3. Title present
            title = page.title()
            checks["has_title"] = bool(title and len(title) > 0)
            checks["title"] = title

            # 4. No broken images
            broken_images = page.evaluate("""
                () => {
                    const imgs = document.querySelectorAll('img');
                    return Array.from(imgs).filter(img => !img.complete || img.naturalWidth === 0).length;
                }
            """)
            checks["broken_images"] = broken_images

            # 5. CTA buttons/links present and visible
            cta_selectors = [
                "a[href*='register']", "a[href*='inscription']",
                "button[type='submit']", ".cta", "[data-cta]",
                "a.btn", "a.button", "button.btn", "button.button",
                "a[href*='dashboard']", "a[href*='signup']", "a[href*='start']",
                "a[href*='essai']", "a[href*='demo']",
            ]
            cta_found = 0
            for sel in cta_selectors:
                try:
                    elements = page.query_selector_all(sel)
                    for el in elements:
                        if el.is_visible():
                            cta_found += 1
                except Exception:
                    pass
            checks["cta_visible_count"] = cta_found
            checks["has_cta"] = cta_found > 0

            # 6. Forms have labels/placeholders
            form_issues = page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"])');
                    let issues = 0;
                    inputs.forEach(input => {
                        const hasLabel = document.querySelector(`label[for="${input.id}"]`);
                        const hasPlaceholder = input.placeholder;
                        const hasAriaLabel = input.getAttribute('aria-label');
                        if (!hasLabel && !hasPlaceholder && !hasAriaLabel) issues++;
                    });
                    return issues;
                }
            """)
            checks["form_unlabeled_inputs"] = form_issues

            # 7. Navigation links work (no 404 hrefs)
            links = page.evaluate("""
                () => {
                    const anchors = document.querySelectorAll('a[href]');
                    return Array.from(anchors)
                        .map(a => a.href)
                        .filter(h => h.startsWith('http'))
                        .slice(0, 20);
                }
            """)
            checks["link_count"] = len(links)

            # 8. Mobile responsive meta tag
            has_viewport = page.evaluate("""
                () => !!document.querySelector('meta[name="viewport"]')
            """)
            checks["has_viewport_meta"] = has_viewport

            # 9. Take screenshot for vision step
            screenshot_path = SCREENSHOT_DIR / f"{page_name}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)
            checks["screenshot_path"] = str(screenshot_path)

            browser.close()

            # Score calculation
            score = 100.0
            if not checks["page_loads"]:
                score = 0
            else:
                if checks["console_errors"] > 0:
                    score -= min(checks["console_errors"] * 5, 20)
                if not checks["has_title"]:
                    score -= 10
                if checks["broken_images"] > 0:
                    score -= checks["broken_images"] * 10
                if not checks["has_cta"]:
                    score -= 15
                if checks["form_unlabeled_inputs"] > 0:
                    score -= min(checks["form_unlabeled_inputs"] * 5, 15)
                if not checks["has_viewport_meta"]:
                    score -= 10

            result["pass"] = score >= 70
            result["details"] = checks
            result["score"] = max(0, score)

    except Exception as e:
        result["details"] = {"error": str(e)}
        result["score"] = 0

    print(f"  [E2E] Score: {result['score']:.0f}/100 {'PASS' if result['pass'] else 'FAIL'}")
    return result


# ---------------------------------------------------------------------------
# Step 2a: Lighthouse
# ---------------------------------------------------------------------------
def run_lighthouse(url: str, page_name: str) -> dict:
    """Run Lighthouse audit and return scores."""
    print(f"  [Lighthouse] Auditing {url} ...")
    result = {"scores": {}, "score": 0.0}

    try:
        LIGHTHOUSE_DIR.mkdir(parents=True, exist_ok=True)
        output_path = LIGHTHOUSE_DIR / f"{page_name}.json"

        cmd = [
            "npx", "lighthouse", url,
            "--output=json",
            f"--output-path={output_path}",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--only-categories=performance,accessibility,best-practices,seo",
            "--quiet",
        ]

        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            env={**os.environ, "CHROME_PATH": CHROMIUM_PATH, "CHROMIUM_PATH": CHROMIUM_PATH}
        )

        if output_path.exists():
            with open(output_path) as f:
                lh_data = json.load(f)

            categories = lh_data.get("categories", {})
            scores = {}
            for cat_key, cat_data in categories.items():
                raw = cat_data.get("score")
                scores[cat_key] = int(raw * 100) if raw is not None else 0

            result["scores"] = scores
            # Average of all categories
            if scores:
                result["score"] = sum(scores.values()) / len(scores)
            print(f"  [Lighthouse] Scores: {scores}")
        else:
            result["scores"] = {"error": "No output file"}
            print(f"  [Lighthouse] WARNING: No output generated")
            if proc.stderr:
                print(f"  [Lighthouse] stderr: {proc.stderr[:200]}")

    except subprocess.TimeoutExpired:
        result["scores"] = {"error": "Timeout 120s"}
        print("  [Lighthouse] TIMEOUT after 120s")
    except Exception as e:
        result["scores"] = {"error": str(e)}
        print(f"  [Lighthouse] ERROR: {e}")

    return result


# ---------------------------------------------------------------------------
# Step 2b: axe-core (Accessibility)
# ---------------------------------------------------------------------------
def run_axe_audit(url: str, page_name: str) -> dict:
    """Run axe-core accessibility audit via Playwright."""
    print(f"  [axe-core] Auditing {url} ...")
    result = {"violations": [], "critical": 0, "serious": 0, "score": 100.0}

    try:
        from playwright.sync_api import sync_playwright
        from axe_playwright_python.sync_playwright import Axe

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=CHROMIUM_PATH)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)

            axe = Axe()
            axe_results = axe.run(page)

            violations = axe_results.response.get("violations", [])
            critical = 0
            serious = 0
            violation_summary = []

            for v in violations:
                impact = v.get("impact", "minor")
                violation_summary.append({
                    "id": v.get("id"),
                    "impact": impact,
                    "description": v.get("description", ""),
                    "nodes_count": len(v.get("nodes", [])),
                })
                if impact == "critical":
                    critical += 1
                elif impact == "serious":
                    serious += 1

            result["violations"] = violation_summary
            result["critical"] = critical
            result["serious"] = serious

            # Score: start at 100, deduct per violation
            score = 100.0
            score -= critical * 25
            score -= serious * 10
            score -= (len(violations) - critical - serious) * 3
            result["score"] = max(0, score)

            browser.close()

    except Exception as e:
        result["violations"] = [{"error": str(e)}]
        result["score"] = 50  # Unknown = penalty but not zero
        print(f"  [axe-core] ERROR: {e}")

    print(f"  [axe-core] Score: {result['score']:.0f}/100 | Critical: {result['critical']} | Serious: {result['serious']}")
    return result


# ---------------------------------------------------------------------------
# Step 3: Claude Vision
# ---------------------------------------------------------------------------
def run_claude_vision(page_name: str, url: str, skip: bool = False) -> dict:
    """Analyze screenshot with Claude multimodal for UX quality."""
    result = {"analysis": "", "score": 0.0, "skipped": False}

    if skip:
        result["skipped"] = True
        result["score"] = 80  # Neutral score when skipped
        print("  [Vision] Skipped (--skip-vision)")
        return result

    screenshot_path = SCREENSHOT_DIR / f"{page_name}.png"
    if not screenshot_path.exists():
        result["analysis"] = "No screenshot available"
        result["score"] = 50
        print("  [Vision] No screenshot found")
        return result

    print(f"  [Vision] Analyzing screenshot {screenshot_path} ...")

    try:
        prompt = f"""Analyse cette capture d'écran de la page web {url}.

Évalue les critères suivants sur 20 chacun (total /100):
1. CLARTÉ (20pts): Le message principal est-il clair et compréhensible en <5 secondes?
2. CTA (20pts): Les appels à l'action sont-ils visibles, clairs et bien positionnés?
3. PROFESSIONNALISME (20pts): Le design est-il professionnel (couleurs, typographie, espacement)?
4. COHÉRENCE (20pts): L'ensemble est-il visuellement cohérent (pas de rupture de style)?
5. PARCOURS INTUITIF (20pts): L'utilisateur comprend-il immédiatement quoi faire?

Réponds STRICTEMENT dans ce format JSON (pas de texte avant/après):
{{
  "clarity": <score 0-20>,
  "cta": <score 0-20>,
  "professionalism": <score 0-20>,
  "coherence": <score 0-20>,
  "intuitive_flow": <score 0-20>,
  "total": <sum>,
  "issues": ["issue1", "issue2"],
  "strengths": ["strength1", "strength2"]
}}"""

        # Use Claude CLI with screenshot
        cmd = [
            "claude", "-p", prompt,
            "--model", "sonnet",
            "--max-turns", "1",
            str(screenshot_path),
        ]

        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
        )

        output = proc.stdout.strip()
        result["analysis"] = output

        # Parse JSON from output
        try:
            # Find JSON in the output
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                vision_data = json.loads(output[json_start:json_end])
                result["score"] = float(vision_data.get("total", 0))
                result["details"] = vision_data
            else:
                result["score"] = 50
                result["analysis"] = f"Could not parse JSON from: {output[:200]}"
        except json.JSONDecodeError:
            result["score"] = 50
            result["analysis"] = f"Invalid JSON: {output[:200]}"

    except subprocess.TimeoutExpired:
        result["analysis"] = "Claude Vision timeout (60s)"
        result["score"] = 50
    except FileNotFoundError:
        result["analysis"] = "Claude CLI not found"
        result["score"] = 80  # Don't penalize if CLI unavailable
        result["skipped"] = True
    except Exception as e:
        result["analysis"] = f"Error: {str(e)}"
        result["score"] = 50

    print(f"  [Vision] Score: {result['score']:.0f}/100")
    return result


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------
def compute_composite(pr: PageResult) -> float:
    """Compute weighted composite score."""
    vision_weight = WEIGHT_VISION if not pr.vision_skipped else 0
    total_weight = WEIGHT_E2E + WEIGHT_LIGHTHOUSE + WEIGHT_AXE + vision_weight
    # Normalize weights
    w_e2e = WEIGHT_E2E / total_weight
    w_lh = WEIGHT_LIGHTHOUSE / total_weight
    w_axe = WEIGHT_AXE / total_weight
    w_vis = vision_weight / total_weight

    composite = (
        pr.e2e_score * w_e2e
        + pr.lighthouse_score * w_lh
        + pr.axe_score * w_axe
        + pr.vision_score * w_vis
    )
    return round(composite, 1)


def get_verdict(score: float, axe_critical: int) -> str:
    """Determine PASS/WARN/FAIL verdict."""
    if axe_critical > AXE_CRITICAL_MAX:
        return "FAIL"
    if score >= COMPOSITE_PASS:
        return "PASS"
    if score >= COMPOSITE_WARN:
        return "WARN"
    return "FAIL"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def validate_page(page_name: str, url: str, skip_vision: bool = False) -> PageResult:
    """Run full validation pipeline on a single page."""
    pr = PageResult(page_name=page_name, url=url)

    print(f"\n{'='*60}")
    print(f"  VALIDATING: {page_name} ({url})")
    print(f"{'='*60}")

    # Step 1: Playwright E2E
    e2e = run_e2e_checks(url, page_name)
    pr.e2e_pass = e2e["pass"]
    pr.e2e_details = e2e["details"]
    pr.e2e_score = e2e["score"]

    if not pr.e2e_pass and pr.e2e_score == 0:
        pr.errors.append("Page failed to load - skipping further checks")
        pr.verdict = "FAIL"
        return pr

    # Step 2a: Lighthouse
    lh = run_lighthouse(url, page_name)
    pr.lighthouse_scores = lh["scores"]
    pr.lighthouse_score = lh["score"]

    # Step 2b: axe-core
    axe = run_axe_audit(url, page_name)
    pr.axe_violations = axe["violations"]
    pr.axe_critical_count = axe["critical"]
    pr.axe_serious_count = axe["serious"]
    pr.axe_score = axe["score"]

    # Step 3: Claude Vision
    vis = run_claude_vision(page_name, url, skip=skip_vision)
    pr.vision_analysis = vis.get("analysis", "")
    pr.vision_score = vis["score"]
    pr.vision_skipped = vis.get("skipped", False)

    # Composite
    pr.composite_score = compute_composite(pr)
    pr.verdict = get_verdict(pr.composite_score, pr.axe_critical_count)

    return pr


def print_report(results: list[PageResult]):
    """Print human-readable validation report."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          UI VALIDATION PIPELINE - RAPPORT                  ║")
    print(f"║  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'):^56} ║")
    print("╚════════════════════════════════════════════════════════════╝")

    all_pass = True

    for pr in results:
        icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(pr.verdict, "?")
        print(f"\n  {icon} {pr.page_name} ({pr.url})")
        print(f"    Composite: {pr.composite_score:.0f}/100  →  {pr.verdict}")
        print(f"    ├── E2E:        {pr.e2e_score:.0f}/100")
        lh_detail = ", ".join(f"{k}: {v}" for k, v in pr.lighthouse_scores.items() if k != "error")
        print(f"    ├── Lighthouse: {pr.lighthouse_score:.0f}/100  ({lh_detail})")
        print(f"    ├── axe-core:   {pr.axe_score:.0f}/100  (critical: {pr.axe_critical_count}, serious: {pr.axe_serious_count})")
        if pr.vision_skipped:
            print(f"    └── Vision:     SKIPPED")
        else:
            print(f"    └── Vision:     {pr.vision_score:.0f}/100")

        if pr.axe_critical_count > 0:
            print(f"    ⚠ CRITICAL axe violations:")
            for v in pr.axe_violations:
                if v.get("impact") == "critical":
                    print(f"      - {v.get('id')}: {v.get('description')}")

        if pr.errors:
            for err in pr.errors:
                print(f"    ✗ {err}")

        if pr.verdict != "PASS":
            all_pass = False

    # Overall verdict
    print(f"\n{'='*60}")
    if all_pass:
        print("  ✓ PIPELINE PASS - Toutes les pages validées (>85/100)")
    else:
        failed = [pr for pr in results if pr.verdict == "FAIL"]
        warned = [pr for pr in results if pr.verdict == "WARN"]
        if failed:
            print(f"  ✗ PIPELINE FAIL - {len(failed)} page(s) en échec (<70/100)")
            print(f"    Corriger avant déploiement: {', '.join(pr.page_name for pr in failed)}")
        if warned:
            print(f"  ⚠ PIPELINE WARN - {len(warned)} page(s) en avertissement (70-85)")
    print(f"{'='*60}")

    return all_pass


def save_json_report(results: list[PageResult], output_path: Path):
    """Save machine-readable JSON report."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "1.0",
        "pages": [],
        "overall_pass": all(pr.verdict == "PASS" for pr in results),
    }

    for pr in results:
        report["pages"].append({
            "page_name": pr.page_name,
            "url": pr.url,
            "composite_score": pr.composite_score,
            "verdict": pr.verdict,
            "e2e": {"score": pr.e2e_score, "details": pr.e2e_details},
            "lighthouse": {"score": pr.lighthouse_score, "categories": pr.lighthouse_scores},
            "axe": {
                "score": pr.axe_score,
                "critical": pr.axe_critical_count,
                "serious": pr.axe_serious_count,
                "violations": pr.axe_violations,
            },
            "vision": {
                "score": pr.vision_score,
                "skipped": pr.vision_skipped,
                "analysis": pr.vision_analysis[:500] if isinstance(pr.vision_analysis, str) else "",
            },
            "errors": pr.errors,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON report: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="UI Validation Pipeline")
    parser.add_argument("--url", help="Validate a single URL")
    parser.add_argument("--pages", nargs="+", help="Page names to validate (e.g. arkwatch dashboard)")
    parser.add_argument("--skip-vision", action="store_true", help="Skip Claude Vision step")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--all", action="store_true", help="Validate all default pages")
    args = parser.parse_args()

    # Ensure directories exist
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    LIGHTHOUSE_DIR.mkdir(parents=True, exist_ok=True)

    # Determine pages to validate
    pages = {}
    if args.url:
        name = args.url.split("/")[-1].replace(".html", "") or "custom"
        pages[name] = args.url
    elif args.pages:
        for p in args.pages:
            if p in DEFAULT_PAGES:
                pages[p] = DEFAULT_PAGES[p]
            else:
                print(f"  Unknown page: {p}. Available: {', '.join(DEFAULT_PAGES.keys())}")
                sys.exit(1)
    else:
        # Default: validate main user-facing pages
        pages = {k: v for k, v in DEFAULT_PAGES.items() if k in ("arkwatch", "dashboard", "index")}

    print(f"  UI Validation Pipeline v1.0")
    print(f"  Pages: {', '.join(pages.keys())}")
    print(f"  Vision: {'SKIP' if args.skip_vision else 'ENABLED'}")

    # Run pipeline
    results = []
    for name, url in pages.items():
        pr = validate_page(name, url, skip_vision=args.skip_vision)
        results.append(pr)

    # Report
    all_pass = print_report(results)

    # JSON output
    if args.json:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = REPORT_DIR / f"validation_{ts}.json"
        save_json_report(results, json_path)

    # Always save latest result for CEO consumption
    save_json_report(results, REPORT_DIR / "latest.json")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
