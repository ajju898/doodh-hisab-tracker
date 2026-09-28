import os
import sys
import time
import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("DairyTracker")

from dairy_tracker_config import (
    TARGET_KEYWORDS,
    DAILY_NEW_APPS_LIMIT,
    CHECK_INTERVAL_HOURS,
    MAX_REVIEWS_PER_CHECK,
    DATABASE_PATH
)
from dairy_tracker_db import (
    init_db,
    add_to_discovered_pool,
    get_pending_apps_from_pool,
    upsert_tracked_app,
    get_all_tracked_apps,
    record_review_if_new,
    get_summary_stats
)
from telegram_notifier import (
    send_telegram_message,
    notify_app_update,
    notify_new_review,
    notify_daily_batch_added,
    notify_summary,
    test_telegram_connection,
    is_telegram_configured
)
from playstore_service import (
    search_playstore,
    fetch_full_app_details,
    fetch_latest_reviews,
    SCRAPER_AVAILABLE
)

def run_discovery() -> int:
    """Scans all dairy/milk keywords on Play Store and pools candidate apps."""
    logger.info("🔎 Starting Play Store keyword discovery for 'Doodh ka Hisab' apps...")
    total_new = 0
    for kw in TARGET_KEYWORDS:
        logger.info(f"  Searching keyword: '{kw}'...")
        apps = search_playstore(kw, n_hits=40)
        new_count = add_to_discovered_pool(apps, kw)
        logger.info(f"  Found {len(apps)} apps matching keyword ({new_count} newly added to pool).")
        total_new += new_count
        time.sleep(1) # Be gentle with Play Store requests
        
    stats = get_summary_stats()
    logger.info(f"✅ Discovery complete! {total_new} new apps discovered. Total pool: {stats['total_discovered']} ({stats['pending_discovery']} pending).")
    return total_new

def run_add_daily_batch(limit: int = DAILY_NEW_APPS_LIMIT) -> int:
    """Takes up to `limit` pending apps from the pool, fetches full data, and starts tracking them."""
    pending = get_pending_apps_from_pool(limit=limit)
    if not pending:
        logger.info("ℹ️ No pending apps in the pool. All discovered apps are already being tracked!")
        return 0

    logger.info(f"🚀 Promoting {len(pending)} apps from discovery pool to active 24/7 tracking...")
    added_apps = []
    
    for item in pending:
        app_id = item["app_id"]
        logger.info(f"  Fetching details for: {item.get('title')} ({app_id})...")
        details = fetch_full_app_details(app_id)
        if details:
            is_new, _ = upsert_tracked_app(details)
            added_apps.append(details)
        time.sleep(1)

    stats = get_summary_stats()
    if added_apps:
        notify_daily_batch_added(added_apps, stats["pending_discovery"])
        logger.info(f"✅ Successfully added {len(added_apps)} apps to active tracking! Notification sent to Telegram.")
    return len(added_apps)

def run_scan_updates() -> int:
    """Checks all actively tracked apps for version bumps, changelog changes, or rating changes."""
    tracked = get_all_tracked_apps()
    if not tracked:
        logger.warning("No apps are currently being tracked. Run --add-batch first!")
        return 0

    logger.info(f"🔄 Scanning {len(tracked)} active apps for updates, changelogs, and rating changes...")
    updates_found = 0
    
    for app in tracked:
        app_id = app["app_id"]
        title = app["title"]
        app_url = app["url"]
        
        details = fetch_full_app_details(app_id)
        if not details:
            continue
            
        is_new, changes = upsert_tracked_app(details)
        if changes:
            updates_found += 1
            logger.info(f"🚨 UPDATE DETECTED for '{title}': {len(changes)} changes found!")
            notify_app_update(title, app_id, changes, app_url)
            
        time.sleep(0.5)
        
    logger.info(f"✅ Update scan complete! {updates_found} apps had new updates.")
    return updates_found

def run_scan_reviews(max_reviews: int = MAX_REVIEWS_PER_CHECK) -> int:
    """Scans for new user reviews across all tracked apps."""
    tracked = get_all_tracked_apps()
    if not tracked:
        return 0

    logger.info(f"💬 Scanning {len(tracked)} tracked apps for new user reviews...")
    new_reviews_count = 0
    
    for app in tracked:
        app_id = app["app_id"]
        title = app["title"]
        app_url = app["url"]
        
        reviews = fetch_latest_reviews(app_id, count=max_reviews)
        for r in reviews:
            is_new = record_review_if_new(app_id, r)
            if is_new:
                new_reviews_count += 1
                logger.info(f"💬 New review on '{title}': {r.get('score')}⭐ by {r.get('userName')}")
                notify_new_review(title, r, app_url)
                time.sleep(0.3)
                
        time.sleep(0.5)
        
    logger.info(f"✅ Review scan complete! {new_reviews_count} new reviews captured and alerted.")
    return new_reviews_count

def export_to_csv(filename: str = "dairy_competitors_list.csv"):
    """Exports all tracked apps with full details to a clean CSV file."""
    tracked = get_all_tracked_apps()
    if not tracked:
        logger.warning("No tracked apps to export.")
        return

    filepath = Path(filename)
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "title", "app_id", "developer", "score", "ratings_count",
            "reviews_count", "installs", "version", "last_updated",
            "recent_changes", "url", "last_checked_at"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in tracked:
            writer.writerow(row)
            
    logger.info(f"📁 Exported {len(tracked)} apps to {filepath.resolve()}")

def run_full_cycle():
    """Runs the complete automation loop: Discover -> Add daily batch -> Check updates -> Check reviews -> Report."""
    logger.info("==================================================")
    logger.info("🚀 RUNNING FULL COMPETITOR RADAR CYCLE")
    logger.info("==================================================")
    
    # 1. Discover newly launched competitor apps
    run_discovery()
    
    # 2. Add daily batch of 10 apps to active tracking
    run_add_daily_batch()
    
    # 3. Check existing active apps for updates/changelogs
    run_scan_updates()
    
    # 4. Check for new customer reviews
    run_scan_reviews()
    
    # 5. Send daily summary digest
    stats = get_summary_stats()
    notify_summary(stats)
    logger.info("🎉 Full cycle finished successfully!")

def run_daemon_scheduler():
    """Runs continuously in the background, checking periodically."""
    logger.info(f"🕒 Starting 24/7 background monitor (Cycle interval: every {CHECK_INTERVAL_HOURS} hours)...")
    logger.info("Press Ctrl+C to stop.")
    
    while True:
        try:
            run_full_cycle()
        except Exception as e:
            logger.error(f"Error during cycle: {e}")
            
        sleep_seconds = CHECK_INTERVAL_HOURS * 3600
        logger.info(f"💤 Sleeping for {CHECK_INTERVAL_HOURS} hours until next scan...")
        time.sleep(sleep_seconds)

def interactive_menu():
    """Interactive command-line studio for testing and manual triggers."""
    init_db()
    
    while True:
        stats = get_summary_stats()
        print("\n" + "=" * 55)
        print("  🥛 DOODH KA HISAB - COMPETITOR INTELLIGENCE RADAR")
        print("=" * 55)
        print(f"  🔍 Total Discovered Apps:  {stats['total_discovered']}")
        print(f"  ⏳ Pending in Queue:       {stats['pending_discovery']}")
        print(f"  🚀 Actively Tracked Apps:  {stats['actively_tracked']}")
        print(f"  💬 Reviews Captured:       {stats['total_reviews_captured']}")
        print(f"  🔄 Updates Detected:       {stats['total_updates_detected']}")
        print(f"  📱 Telegram Status:        {'Connected ✅' if is_telegram_configured() else 'Not Configured ⚠️'}")
        print("-" * 55)
        print("1. 🔎 Discover All Competitor Apps (Search Play Store)")
        print("2. 🎯 Add Next 10 Apps to Active Tracking (Daily Batch)")
        print("3. 🔄 Check for App Updates & Changelog Changes Now")
        print("4. 💬 Check for New User Reviews Now")
        print("5. 🚀 Run Full Automation Cycle (Discover + Add 10 + Scan)")
        print("6. 🕒 Start 24/7 Background Scheduler Worker")
        print("7. 📁 Export Tracked Competitor List to CSV (Excel)")
        print("8. 🤖 Test Telegram Bot Alert Message")
        print("0. ❌ Exit")
        print("-" * 55)
        
        choice = input("Enter your choice (0-8): ").strip()
        
        if choice == "1":
            run_discovery()
        elif choice == "2":
            run_add_daily_batch()
        elif choice == "3":
            run_scan_updates()
        elif choice == "4":
            run_scan_reviews()
        elif choice == "5":
            run_full_cycle()
        elif choice == "6":
            run_daemon_scheduler()
        elif choice == "7":
            export_to_csv()
        elif choice == "8":
            if is_telegram_configured():
                test_telegram_connection()
                print("✅ Test message sent! Check your Telegram chat.")
            else:
                print("⚠️ Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first.")
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice, please select 0-8.")

def main():
    init_db()
    parser = argparse.ArgumentParser(description="Doodh Ka Hisab Competitor Intelligence Automation")
    parser.add_argument("--discover", action="store_true", help="Discover apps from Play Store")
    parser.add_argument("--add-batch", action="store_true", help="Add daily batch of 10 apps to tracking")
    parser.add_argument("--scan-updates", action="store_true", help="Scan active apps for version updates")
    parser.add_argument("--scan-reviews", action="store_true", help="Scan active apps for new reviews")
    parser.add_argument("--run", action="store_true", help="Run full cycle once")
    parser.add_argument("--daemon", action="store_true", help="Run continuous background loop")
    parser.add_argument("--export", action="store_true", help="Export tracked apps to CSV")
    parser.add_argument("--test-telegram", action="store_true", help="Send test message to Telegram")
    
    args = parser.parse_args()
    
    if args.discover:
        run_discovery()
    elif args.add_batch:
        run_add_daily_batch()
    elif args.scan_updates:
        run_scan_updates()
    elif args.scan_reviews:
        run_scan_reviews()
    elif args.run:
        run_full_cycle()
    elif args.daemon:
        run_daemon_scheduler()
    elif args.export:
        export_to_csv()
    elif args.test_telegram:
        test_telegram_connection()
    else:
        # Default to interactive menu if no arguments passed
        interactive_menu()

if __name__ == "__main__":
    main()
