#!/usr/bin/env python3
"""ArkWatch Analytics Report — reads nginx tracking.log and outputs traffic stats.

Usage:
    python3 analytics_report.py              # Today's stats
    python3 analytics_report.py --days 7     # Last 7 days
    python3 analytics_report.py --all        # All time
"""
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_FILE = Path("/var/log/nginx/tracking.log")
# Log format: timestamp|ip|event|page|source|referer|user_agent
# Older entries (before source field added) have format:
# timestamp|ip|event|page|referer|user_agent


def parse_line(line):
    parts = line.strip().split("|")
    if len(parts) == 7:
        ts, ip, event, page, source, referer, ua = parts
    elif len(parts) == 6:
        ts, ip, event, page, referer, ua = parts
        source = "-"
    else:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("+00:00", "+00:00"))
    except Exception:
        try:
            dt = datetime.fromisoformat(ts[:19])
        except Exception:
            return None
    return {
        "ts": dt, "ip": ip, "event": event or "-",
        "page": page or "-", "source": source or "-",
        "referer": referer or "-", "ua": ua or "-",
    }


def load_entries(since=None):
    if not LOG_FILE.exists():
        return []
    entries = []
    with open(LOG_FILE) as f:
        for line in f:
            entry = parse_line(line)
            if entry is None:
                continue
            if since and entry["ts"].replace(tzinfo=None) < since.replace(tzinfo=None):
                continue
            entries.append(entry)
    return entries


def report(entries):
    if not entries:
        print("Aucune donnée de tracking trouvée.")
        return

    # Filter to arkwatch page only
    arkwatch = [e for e in entries if "/arkwatch" in e["page"]]
    all_pages = entries  # keep all for global view

    print("=" * 60)
    print("  ARKWATCH ANALYTICS REPORT")
    print(f"  Période: {entries[0]['ts'].strftime('%Y-%m-%d %H:%M')} → {entries[-1]['ts'].strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # --- Global stats ---
    events = Counter(e["event"] for e in arkwatch)
    print(f"\n📊 ÉVÉNEMENTS (arkwatch.html)")
    print(f"  Pageviews:       {events.get('pageview', 0)}")
    print(f"  CTA clicks:      {events.get('cta_click', 0)}")
    print(f"  Signup attempts: {events.get('signup_attempt', 0)}")
    print(f"  Signup success:  {events.get('signup_success', 0)}")
    pv = events.get("pageview", 0)
    if pv > 0:
        cta_rate = events.get("cta_click", 0) / pv * 100
        signup_rate = events.get("signup_attempt", 0) / pv * 100
        conv_rate = events.get("signup_success", 0) / pv * 100
        print(f"\n  CTA click rate:   {cta_rate:.1f}%")
        print(f"  Signup rate:      {signup_rate:.1f}%")
        print(f"  Conversion rate:  {conv_rate:.1f}%")

    # --- Source breakdown ---
    sources = Counter(e["source"] for e in arkwatch if e["event"] == "pageview")
    print(f"\n🔗 SOURCES DE TRAFIC (pageviews)")
    for src, count in sources.most_common(15):
        pct = count / pv * 100 if pv > 0 else 0
        print(f"  {src:20s} {count:5d}  ({pct:.1f}%)")

    # --- Source conversion funnel ---
    print(f"\n🎯 FUNNEL PAR SOURCE")
    src_events = defaultdict(Counter)
    for e in arkwatch:
        src_events[e["source"]][e["event"]] += 1
    print(f"  {'Source':<20s} {'Views':>6} {'CTA':>6} {'Signup':>7} {'Conv':>6} {'Rate':>6}")
    print(f"  {'-'*20} {'-'*6} {'-'*6} {'-'*7} {'-'*6} {'-'*6}")
    for src, _ in sources.most_common(15):
        ev = src_events[src]
        v = ev.get("pageview", 0)
        c = ev.get("cta_click", 0)
        s = ev.get("signup_attempt", 0)
        ok = ev.get("signup_success", 0)
        rate = f"{ok/v*100:.1f}%" if v > 0 else "-"
        print(f"  {src:<20s} {v:>6} {c:>6} {s:>7} {ok:>6} {rate:>6}")

    # --- Daily breakdown ---
    daily = defaultdict(lambda: Counter())
    for e in arkwatch:
        day = e["ts"].strftime("%Y-%m-%d")
        daily[day][e["event"]] += 1
    if daily:
        print(f"\n📅 PAR JOUR")
        print(f"  {'Date':<12s} {'Views':>6} {'CTA':>6} {'Signup':>7} {'Conv':>6}")
        print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*7} {'-'*6}")
        for day in sorted(daily.keys()):
            ev = daily[day]
            print(f"  {day:<12s} {ev.get('pageview',0):>6} {ev.get('cta_click',0):>6} {ev.get('signup_attempt',0):>7} {ev.get('signup_success',0):>6}")

    # --- Unique visitors ---
    unique_ips = len(set(e["ip"] for e in arkwatch if e["event"] == "pageview"))
    print(f"\n👤 Visiteurs uniques (par IP): {unique_ips}")

    # --- All pages overview ---
    pages = Counter(e["page"] for e in all_pages if e["event"] == "pageview")
    if len(pages) > 1:
        print(f"\n📄 TOUTES LES PAGES (pageviews)")
        for page, count in pages.most_common(10):
            print(f"  {page:<40s} {count:>5}")

    print("\n" + "=" * 60)


def main():
    days = None
    if "--all" in sys.argv:
        since = None
    elif "--days" in sys.argv:
        idx = sys.argv.index("--days")
        days = int(sys.argv[idx + 1])
        since = datetime.now(timezone.utc) - timedelta(days=days)
    else:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    entries = load_entries(since)
    report(entries)


if __name__ == "__main__":
    main()
