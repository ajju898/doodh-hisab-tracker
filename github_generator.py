import os
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any
from dairy_tracker_db import (
    get_connection,
    get_all_tracked_apps,
    get_summary_stats
)

BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / "apps"
CHANGES_DIR = BASE_DIR / "changes"

def ensure_dirs():
    APPS_DIR.mkdir(exist_ok=True)
    CHANGES_DIR.mkdir(exist_ok=True)

def generate_apps_section() -> str:
    """Generates the apps/ directory and master apps list markdown."""
    apps = get_all_tracked_apps()
    
    # 1. Generate individual markdown files for each app
    with get_connection() as conn:
        cursor = conn.cursor()
        for app in apps:
            app_id = app["app_id"]
            title = app["title"]
            developer = app["developer"]
            score = app["score"] or 0.0
            ratings_count = app["ratings_count"] or 0
            reviews_count = app["reviews_count"] or 0
            installs = app["installs"] or "N/A"
            version = app["version"] or "N/A"
            last_updated = app["last_updated"] or "N/A"
            recent_changes = app["recent_changes"] or "No release notes provided."
            description = app["description"] or "No description provided."
            url = app["url"]
            
            # Fetch reviews for this app with full metadata
            cursor.execute("""
                SELECT user_name, score, content, review_created_at, thumbs_up_count, app_version, developer_reply, reply_date
                FROM reviews
                WHERE app_id = ?
                ORDER BY detected_at DESC
                LIMIT 20
            """, (app_id,))
            recent_reviews = cursor.fetchall()
            
            # Fetch history for this app
            cursor.execute("""
                SELECT change_type, old_value, new_value, detected_at
                FROM app_history
                WHERE app_id = ?
                ORDER BY detected_at DESC
                LIMIT 10
            """, (app_id,))
            history_rows = cursor.fetchall()
            
        app_md_content = [
            f"# 📱 {title}",
            "",
            f"- **App ID (Package):** `{app_id}`",
            f"- **Developer:** {developer}",
            f"- **Rating:** ⭐ {score} ({ratings_count:,} ratings | {reviews_count:,} reviews)",
            f"- **Installs:** {installs}",
            f"- **Current Version:** `{version}`",
            f"- **Last Updated Date:** {last_updated}",
            f"- **Play Store Link:** [Open in Google Play]({url})",
            "",
            "## 📝 What's New (Latest Release Notes)",
            f"> {recent_changes.strip()}",
            "",
            "## 🔄 Recent Change History",
        ]
        
        if history_rows:
            app_md_content.append("| Date | Change Type | Old Value | New Value |")
            app_md_content.append("|---|---|---|---|")
            for h in history_rows:
                app_md_content.append(f"| {h['detected_at'][:10]} | `{h['change_type']}` | {h['old_value']} | **{h['new_value']}** |")
        else:
            app_md_content.append("*No updates detected yet since tracking started.*")
            
        app_md_content.extend([
            "",
            "## 💬 Detailed User Reviews & Feedback",
        ])
        
        if recent_reviews:
            for r in recent_reviews:
                stars = "⭐" * int(r["score"] or 0)
                content = (r["content"] or "").replace("\n", " ").strip()
                thumbs = f" | 👍 {r['thumbs_up_count']} helpful" if r["thumbs_up_count"] else ""
                version_info = f" (on `{r['app_version']}`)" if r["app_version"] else ""
                app_md_content.append(f"- **{stars} by {r['user_name']}**{version_info} — *{r['review_created_at']}*{thumbs}")
                app_md_content.append(f"  > \"{content}\"")
                if r["developer_reply"]:
                    dev_reply = r["developer_reply"].replace("\n", " ").strip()
                    app_md_content.append(f"  > 👨‍💻 *Developer Reply ({r['reply_date']}):* \"{dev_reply}\"")
                app_md_content.append("")
        else:
            app_md_content.append("*No reviews logged yet.*")
            
        app_md_content.extend([
            "",
            "## 📖 Full Store Description",
            "<details>",
            "<summary>Click to read full description</summary>",
            "",
            description,
            "",
            "</details>"
        ])
        
        app_file = APPS_DIR / f"{app_id}.md"
        with open(app_file, "w", encoding="utf-8") as f:
            f.write("\n".join(app_md_content))

    # 2. Master apps list in apps/README.md
    master_lines = [
        "# 📱 Tracked Competitor Apps List",
        "",
        f"Currently tracking **{len(apps)} active apps** in the Doodh Ka Hisab / Dairy category.",
        "",
        "| App Name | Developer | Rating ⭐ | Installs | Version | Last Updated | Details |",
        "|---|---|---|---|---|---|---|"
    ]
    for app in apps:
        title = app["title"].replace("|", "-")
        dev = app["developer"].replace("|", "-")
        score = app["score"] or 0.0
        installs = app["installs"] or "N/A"
        version = app["version"] or "N/A"
        updated = str(app["last_updated"])[:10]
        app_id = app["app_id"]
        detail_link = f"[{title}](./{app_id}.md)"
        master_lines.append(f"| {detail_link} | {dev} | {score} ⭐ | {installs} | `{version}` | {updated} | [View Details](./{app_id}.md) |")
        
    master_file = APPS_DIR / "README.md"
    with open(master_file, "w", encoding="utf-8") as f:
        f.write("\n".join(master_lines))
        
    return "\n".join(master_lines)

def generate_changes_section() -> str:
    """Generates daily changelog in changes/ directory."""
    today_str = datetime.date.today().isoformat()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get changes
        cursor.execute("""
            SELECT h.app_id, t.title, h.change_type, h.old_value, h.new_value, h.detected_at
            FROM app_history h
            LEFT JOIN tracked_apps t ON h.app_id = t.app_id
            ORDER BY h.detected_at DESC
        """)
        all_changes = cursor.fetchall()
        
        # Get recently captured reviews
        cursor.execute("""
            SELECT r.app_id, t.title, r.user_name, r.score, r.content, r.detected_at
            FROM reviews r
            LEFT JOIN tracked_apps t ON r.app_id = t.app_id
            ORDER BY r.detected_at DESC
            LIMIT 50
        """)
        recent_reviews = cursor.fetchall()

    changes_lines = [
        "# 🔄 Competitor Changes & Activity Log",
        "",
        f"Last updated: **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**",
        "",
        "## 🚨 App Updates & Modifications",
    ]
    
    if all_changes:
        changes_lines.append("| Date | App | Change Type | Old Value | New Value |")
        changes_lines.append("|---|---|---|---|---|")
        for ch in all_changes:
            app_title = ch["title"] or ch["app_id"]
            app_link = f"[{app_title}](../apps/{ch['app_id']}.md)"
            dt = ch["detected_at"][:16]
            changes_lines.append(f"| {dt} | {app_link} | `{ch['change_type']}` | {ch['old_value']} | **{ch['new_value']}** |")
    else:
        changes_lines.append("*No app updates detected yet.*")
        
    changes_lines.extend([
        "",
        "## 💬 New User Reviews & Complaints",
    ])
    
    if recent_reviews:
        for r in recent_reviews[:20]:
            app_title = r["title"] or r["app_id"]
            stars = "⭐" * int(r["score"] or 0)
            content = r["content"].replace("\n", " ").strip()
            changes_lines.append(f"- **{stars} on [{app_title}](../apps/{r['app_id']}.md)** by *{r['user_name']}* ({r['detected_at'][:10]})")
            changes_lines.append(f"  > \"{content}\"")
    else:
        changes_lines.append("*No new reviews logged yet.*")
        
    changes_file = CHANGES_DIR / "README.md"
    with open(changes_file, "w", encoding="utf-8") as f:
        f.write("\n".join(changes_lines))
        
    # Also save a dated snapshot e.g. changes/2026-09-28.md
    dated_file = CHANGES_DIR / f"{today_str}.md"
    with open(dated_file, "w", encoding="utf-8") as f:
        f.write("\n".join(changes_lines))
        
    return "\n".join(changes_lines)

def generate_root_readme():
    """Generates the main GitHub repository README with links to apps/ and changes/."""
    stats = get_summary_stats()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    apps = get_all_tracked_apps()
    
    readme = [
        "# 🥛 Doodh Ka Hisab - Competitor Intelligence Tracker",
        "",
        "> Automated 24/7 competitor radar for the **Dairy & Milk Ledger** Android ecosystem.",
        "",
        "## 📊 Live Category Dashboard",
        "",
        f"- 🔍 **Total Discovered Apps:** `{stats['total_discovered']}`",
        f"- ⏳ **Pending in Discovery Pool:** `{stats['pending_discovery']}`",
        f"- 🚀 **Actively Monitored Competitors:** `{stats['actively_tracked']}`",
        f"- 💬 **Total User Reviews Captured:** `{stats['total_reviews_captured']}`",
        f"- 🔄 **Total Updates & Changes Detected:** `{stats['total_updates_detected']}`",
        f"- 🕒 **Last Monitored Cycle:** `{now_str}`",
        "",
        "---",
        "",
        "## 📂 Repository Navigation",
        "",
        "- [**📱 Apps Directory (`apps/`)**](./apps/README.md) — Master list of all tracked competitor apps with version numbers, install counts, ratings, and in-depth details.",
        "- [**🔄 Changes Directory (`changes/`)**](./changes/README.md) — Daily logs of updates, version bumps, changelog changes, and new user reviews.",
        "",
        "---",
        "",
        "## 📱 Top Competitors Overview",
        "",
        "| App Name | Developer | Rating ⭐ | Installs | Version | Details |",
        "|---|---|---|---|---|---|"
    ]
    
    for app in apps[:15]:
        title = app["title"].replace("|", "-")
        dev = app["developer"].replace("|", "-")
        score = app["score"] or 0.0
        installs = app["installs"] or "N/A"
        version = app["version"] or "N/A"
        app_id = app["app_id"]
        readme.append(f"| [{title}](./apps/{app_id}.md) | {dev} | {score} ⭐ | {installs} | `{version}` | [Read Details](./apps/{app_id}.md) |")
        
    if len(apps) > 15:
        readme.append(f"\n*(Showing top 15 of {len(apps)} apps. See full list in [**apps/README.md**](./apps/README.md))*")
        
    readme.extend([
        "",
        "---",
        "",
        "## ⚙️ How It Works",
        "",
        "1. **Discovery Pool**: Scans Indian Play Store for dairy/milk management keywords.",
        "2. **Daily 10 Ingestion**: Promotes 10 pending apps each day until the whole category is covered.",
        "3. **Change Detection**: Captures version bumps, release notes, rating shifts, and new customer reviews.",
        "4. **Telegram Alerts**: Sends instant alerts to the linked Telegram channel/bot.",
        "5. **GitHub Sync**: Automatically updates this repository via GitHub Actions daily."
    ])
    
    root_file = BASE_DIR / "README.md"
    with open(root_file, "w", encoding="utf-8") as f:
        f.write("\n".join(readme))
        
    print(f"✅ Generated root README.md, apps/ ({len(apps)} files), and changes/!")

def generate_web_dashboard_data():
    """Exports data.json for the mobile-responsive GitHub Pages web app."""
    stats = get_summary_stats()
    apps = get_all_tracked_apps()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Recent changes
        cursor.execute("""
            SELECT h.app_id, t.title, h.change_type, h.old_value, h.new_value, h.detected_at
            FROM app_history h
            LEFT JOIN tracked_apps t ON h.app_id = t.app_id
            ORDER BY h.detected_at DESC
            LIMIT 100
        """)
        changes = [dict(row) for row in cursor.fetchall()]
        
        # Recent detailed reviews
        cursor.execute("""
            SELECT r.review_id, r.app_id, t.title as app_title, r.user_name, r.score,
                   r.content, r.review_created_at, r.thumbs_up_count, r.app_version,
                   r.developer_reply, r.reply_date, r.detected_at
            FROM reviews r
            LEFT JOIN tracked_apps t ON r.app_id = t.app_id
            ORDER BY r.detected_at DESC
            LIMIT 500
        """)
        reviews = [dict(row) for row in cursor.fetchall()]

    data = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": stats,
        "apps": apps,
        "changes": changes,
        "reviews": reviews
    }
    
    data_file = BASE_DIR / "data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ Exported data.json for GitHub Pages mobile dashboard!")

def build_github_documentation():
    ensure_dirs()
    generate_apps_section()
    generate_changes_section()
    generate_root_readme()
    generate_web_dashboard_data()

if __name__ == "__main__":
    build_github_documentation()
