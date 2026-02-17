"""ArkWatch Worker - Main processing loop"""

import asyncio
import difflib
from datetime import datetime, timedelta

from .analyzer import ContentAnalyzer
from .notifications import EmailNotifier
from .scraper import WebScraper
from .storage import get_db

# Minimum change ratio to trigger a notification (5%)
# This filters out noise from dynamic sites (votes, timestamps, etc.)
MIN_CHANGE_RATIO = 0.05


class ArkWatchWorker:
    """Main worker that processes all watches"""

    def __init__(self):
        self.scraper = WebScraper()
        self.analyzer = ContentAnalyzer()
        self.db = get_db()
        self.notifier = EmailNotifier()

    async def process_watch(self, watch: dict) -> dict | None:
        """Process a single watch"""
        watch_id = watch["id"]
        url = watch["url"]

        print(f"Processing watch: {watch['name']} ({url})")

        # Scrape the URL
        result = await self.scraper.scrape(url)

        if result.error:
            print(f"Scrape error: {result.error}")
            self.db.update_watch(watch_id, status="error", last_check=datetime.utcnow().isoformat())
            return None

        # Check for changes
        previous_hash = watch.get("last_content_hash")
        previous_content = watch.get("last_content", "")

        hash_changed = previous_hash is not None and previous_hash != result.content_hash

        # Filter out noise: check if the change is significant enough
        # Use per-watch threshold if set, otherwise global default
        threshold = watch.get("min_change_ratio") or MIN_CHANGE_RATIO
        changes_detected = False
        if hash_changed and previous_content:
            similarity = difflib.SequenceMatcher(None, previous_content, result.text_content[:10000]).ratio()
            change_ratio = 1.0 - similarity
            if change_ratio >= threshold:
                changes_detected = True
                print(f"  Significant change: {change_ratio:.1%}")
            else:
                print(f"  Minor change filtered: {change_ratio:.1%} (threshold: {threshold:.0%})")
        elif hash_changed and previous_hash is not None:
            # No previous content to compare against - skip notification
            # on first cycle after content is lost; content will be stored
            # for proper comparison on the next cycle.
            print("  Hash changed but no previous content to compare; skipping notification")

        # Update watch with new content
        self.db.update_watch(
            watch_id,
            last_check=datetime.utcnow().isoformat(),
            last_content_hash=result.content_hash,
            last_content=result.text_content[:10000],  # Limit stored content
            status="active",
        )

        # If changes detected, analyze and report
        report = None
        if changes_detected:
            print(f"Changes detected for {watch['name']}!")

            # Compute diff
            has_diff, diff_text = self.scraper.compute_diff(previous_content, result.text_content)

            # Analyze with AI
            analysis = await self.analyzer.analyze_changes(url, previous_content, result.text_content, diff_text)

            # Create report
            report = self.db.create_report(
                watch_id=watch_id,
                changes_detected=True,
                previous_hash=previous_hash,
                current_hash=result.content_hash,
                diff=diff_text[:5000],
                ai_summary=analysis.summary,
                ai_importance=analysis.importance,
            )

            # Send notification if email configured
            if watch.get("notify_email"):
                self.notifier.send_alert(
                    to=watch["notify_email"],
                    watch_name=watch["name"],
                    url=url,
                    summary=analysis.summary,
                    importance=analysis.importance,
                    diff=diff_text[:1000],
                )
                self.db.mark_report_notified(report["id"])

        else:
            # No changes, still create a report for tracking
            report = self.db.create_report(
                watch_id=watch_id,
                changes_detected=False,
                current_hash=result.content_hash,
                previous_hash=previous_hash,
            )

        return report

    async def run_cycle(self):
        """Run one processing cycle for all due watches"""
        watches = self.db.get_watches(status="active")

        print(f"\n=== ArkWatch Cycle: {datetime.utcnow().isoformat()} ===")
        print(f"Active watches: {len(watches)}")

        processed = 0
        changes = 0

        for watch in watches:
            # Check if watch is due
            last_check = watch.get("last_check")
            interval = watch.get("check_interval", 3600)

            if last_check:
                last_dt = datetime.fromisoformat(last_check.replace("Z", ""))
                next_check = last_dt + timedelta(seconds=interval)
                if datetime.utcnow() < next_check:
                    continue  # Not due yet

            report = await self.process_watch(watch)
            processed += 1

            if report and report.get("changes_detected"):
                changes += 1

            # Small delay between requests
            await asyncio.sleep(2)

        print(f"Processed: {processed}, Changes detected: {changes}")
        return processed, changes

    async def run_forever(self, check_interval: int = 300):
        """Run continuously"""
        print("ArkWatch Worker starting...")

        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                print(f"Cycle error: {e}")

            print(f"Sleeping for {check_interval} seconds...")
            await asyncio.sleep(check_interval)


async def main():
    worker = ArkWatchWorker()
    await worker.run_cycle()


if __name__ == "__main__":
    asyncio.run(main())
