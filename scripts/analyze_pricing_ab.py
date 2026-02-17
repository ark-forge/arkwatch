#!/usr/bin/env python3
"""Analyze pricing A/B test results after 100+ visits (24-48h).

Compares conversion rates between v1 (original) and v2 (FOMO/urgency).
Outputs JSON report + text recommendation.

Usage:
    python3 analyze_pricing_ab.py
    python3 analyze_pricing_ab.py --json-only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "pricing_ab_data.json",
)

REPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports",
)


def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def analyze(data):
    v1 = data.get("v1", {})
    v2 = data.get("v2", {})

    v1_views = v1.get("pageviews", 0)
    v1_clicks = v1.get("cta_clicks", 0)
    v2_views = v2.get("pageviews", 0)
    v2_clicks = v2.get("cta_clicks", 0)

    v1_rate = (v1_clicks / v1_views * 100) if v1_views > 0 else 0.0
    v2_rate = (v2_clicks / v2_views * 100) if v2_views > 0 else 0.0

    total = v1_views + v2_views
    sufficient = total >= 100

    # Determine winner
    if not sufficient:
        recommendation = "WAIT"
        reason = f"Only {total}/100 visits collected. Need more data."
    elif v2_rate > v1_rate * 1.1:
        recommendation = "DEPLOY_V2"
        reason = f"V2 (FOMO) converts {v2_rate:.1f}% vs V1 {v1_rate:.1f}% (+{v2_rate - v1_rate:.1f}pp). Deploy pricing-v2.html as default."
    elif v1_rate > v2_rate * 1.1:
        recommendation = "KEEP_V1"
        reason = f"V1 (original) converts {v1_rate:.1f}% vs V2 {v2_rate:.1f}%. Keep pricing.html."
    else:
        recommendation = "TIE"
        reason = f"No significant difference: V1 {v1_rate:.1f}% vs V2 {v2_rate:.1f}%. Consider running longer."

    # Elapsed time
    start = data.get("start_date", "")
    elapsed_hours = 0
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            elapsed_hours = (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600
        except (ValueError, TypeError):
            pass

    report = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_duration_hours": round(elapsed_hours, 1),
        "total_visits": total,
        "sufficient_data": sufficient,
        "v1_original": {
            "pageviews": v1_views,
            "cta_clicks": v1_clicks,
            "conversion_rate_pct": round(v1_rate, 2),
            "sources": v1.get("sources", {}),
        },
        "v2_fomo": {
            "pageviews": v2_views,
            "cta_clicks": v2_clicks,
            "conversion_rate_pct": round(v2_rate, 2),
            "sources": v2.get("sources", {}),
        },
        "recommendation": recommendation,
        "reason": reason,
        "next_action": (
            "Replace pricing.html with pricing-v2.html content"
            if recommendation == "DEPLOY_V2"
            else "Keep current setup"
            if recommendation == "KEEP_V1"
            else "Continue collecting data"
        ),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Analyze pricing A/B test")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    data = load_data()
    if data is None:
        print(json.dumps({"status": "ko", "error": "No A/B data file found. Test not started yet."}))
        sys.exit(1)

    report = analyze(data)

    # Save report
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, "pricing_ab_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    if args.json_only:
        print(json.dumps(report, indent=2))
        return

    # Human-readable output
    print("=" * 60)
    print("  PRICING A/B TEST REPORT")
    print("=" * 60)
    print(f"  Duration: {report['test_duration_hours']}h")
    print(f"  Total visits: {report['total_visits']}")
    print(f"  Sufficient data: {'YES' if report['sufficient_data'] else 'NO (need 100+)'}")
    print()
    print("  V1 (Original pricing.html):")
    print(f"    Pageviews:       {report['v1_original']['pageviews']}")
    print(f"    CTA clicks:      {report['v1_original']['cta_clicks']}")
    print(f"    Conversion rate: {report['v1_original']['conversion_rate_pct']}%")
    print()
    print("  V2 (FOMO/Urgency pricing-v2.html):")
    print(f"    Pageviews:       {report['v2_fomo']['pageviews']}")
    print(f"    CTA clicks:      {report['v2_fomo']['cta_clicks']}")
    print(f"    Conversion rate: {report['v2_fomo']['conversion_rate_pct']}%")
    print()
    print(f"  RECOMMENDATION: {report['recommendation']}")
    print(f"  {report['reason']}")
    print(f"  Next action: {report['next_action']}")
    print("=" * 60)
    print(f"\n  Report saved to: {report_file}")


if __name__ == "__main__":
    main()
