import requests
import html
import logging
from typing import Dict, Any, List, Optional
from dairy_tracker_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

def is_telegram_configured() -> bool:
    """Checks if bot token and chat id are properly set."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and "your_" not in TELEGRAM_BOT_TOKEN)

def send_telegram_message(message_html: str) -> bool:
    """
    Sends an HTML-formatted message to the specified Telegram chat.
    Safe against markdown syntax breaks by using HTML mode.
    """
    if not is_telegram_configured():
        logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

# --- Specialized Alert Formats ---

def notify_app_update(app_title: str, app_id: str, changes: List[Dict[str, str]], app_url: str):
    """Sends an alert when an app is updated, changelog changes, or version bumps."""
    lines = [
        "🚨 <b>COMPETITOR APP UPDATE DETECTED!</b>",
        f"📱 <b>App:</b> <a href=\"{app_url}\">{html.escape(app_title)}</a>",
        f"📦 <code>{html.escape(app_id)}</code>",
        "",
        "<b>Changes Detected:</b>"
    ]
    
    for ch in changes:
        ch_type = ch.get("type")
        old_val = ch.get("old", "N/A")
        new_val = ch.get("new", "N/A")
        
        if ch_type == "VERSION_UPDATE":
            lines.append(f"• <b>Version Bump:</b> <code>{html.escape(old_val)}</code> ➡️ <b><code>{html.escape(new_val)}</code></b>")
        elif ch_type == "WHATS_NEW_CHANGE":
            lines.append("• <b>What's New (Release Notes):</b>")
            lines.append(f"  <i>\"{html.escape(new_val[:300])}\"</i>")
        elif ch_type == "SCORE_CHANGE":
            lines.append(f"• <b>Rating Shift:</b> {old_val} ⭐ ➡️ <b>{new_val} ⭐</b>")
        elif ch_type == "INSTALLS_CHANGE":
            lines.append(f"• <b>Installs Growth:</b> {old_val} ➡️ <b>{new_val}</b>")
        else:
            lines.append(f"• <b>{ch_type}:</b> {html.escape(str(new_val))}")
            
    lines.append("")
    lines.append(f"🔗 <a href=\"{app_url}\">Open in Google Play Store</a>")
    
    send_telegram_message("\n".join(lines))

def notify_new_review(app_title: str, review: Dict[str, Any], app_url: str):
    """Sends an alert when a user leaves a new review on a competitor app."""
    score = review.get("score", 0)
    stars = "⭐" * int(score) if score else "No Rating"
    user_name = review.get("userName") or "Anonymous"
    content = review.get("content") or "<i>No text content</i>"
    date_str = str(review.get("at") or "")
    
    lines = [
        "💬 <b>NEW USER REVIEW ON COMPETITOR APP</b>",
        f"📱 <b>App:</b> <a href=\"{app_url}\">{html.escape(app_title)}</a>",
        f"👤 <b>User:</b> {html.escape(user_name)} ({stars})",
        "",
        f"📝 <b>Review:</b>",
        f"<i>\"{html.escape(content)}\"</i>",
        "",
        f"🕒 <i>{date_str}</i>"
    ]
    send_telegram_message("\n".join(lines))

def notify_reviews_batch_summary(captured_reviews: List[Dict[str, Any]]):
    """Sends a summary digest of captured reviews without flooding Telegram."""
    if not captured_reviews:
        return
        
    total_count = len(captured_reviews)
    lines = [
        "💬 <b>NEW REVIEWS BATCH CAPTURED!</b>",
        f"Captured <b>{total_count} new reviews</b> across competitor apps (Strictly de-duplicated).",
        "",
        "🔥 <b>Key User Complaints & Feedback (Competitor Weaknesses):</b>"
    ]
    
    # Highlight low score / critical reviews first (score <= 2) or top reviews
    critical = [r for r in captured_reviews if (r.get("score") or 5) <= 2]
    highlights = (critical[:4] if critical else captured_reviews[:4])
    
    for r in highlights:
        app_name = html.escape(r.get("app_title", "Competitor App"))
        user = html.escape(r.get("userName") or "User")
        score = r.get("score", 0)
        stars = "⭐" * int(score) if score else ""
        content = html.escape((r.get("content") or "").strip()[:180])
        lines.append(f"• <b>{app_name}</b> ({stars} by <i>{user}</i>):")
        lines.append(f"  \"{content}\"")
        lines.append("")
        
    lines.append(f"📂 <i>All {total_count} detailed reviews saved to database & GitHub.</i>")
    send_telegram_message("\n".join(lines))

def notify_daily_batch_added(added_apps: List[Dict[str, Any]], remaining_pool_count: int):
    """Sends a notification when apps are promoted to active tracking."""
    lines = [
        "🎯 <b>COMPETITOR APPS ADDED TO MONITORING!</b>",
        f"Added <b>{len(added_apps)}</b> apps to active 24/7 tracking.",
        f"⏳ <b>{remaining_pool_count}</b> apps waiting in discovery pool.",
        "",
        "<b>Top Apps Tracked:</b>"
    ]
    
    # Display up to 15 apps to stay well within Telegram's 4096 character limit
    displayed = added_apps[:15]
    for idx, app in enumerate(displayed, start=1):
        title = html.escape(app.get("title", "Unknown App"))
        score = app.get("score") or "N/A"
        installs = app.get("installs") or "N/A"
        app_id = app.get("app_id") or app.get("appId")
        url = app.get("url") or f"https://play.google.com/store/apps/details?id={app_id}"
        lines.append(f"{idx}. <a href=\"{url}\"><b>{title}</b></a> ({score}⭐ | {installs} installs)")
        
    if len(added_apps) > 15:
        lines.append("")
        lines.append(f"<i>...aur <b>{len(added_apps) - 15} aur apps</b> track ho rahe hain! (Poori list GitHub 'apps/' section me available hai).</i>")
        
    lines.append("")
    lines.append("⚡ <i>We are now monitoring updates & reviews for all these apps 24/7!</i>")
    send_telegram_message("\n".join(lines))

def notify_summary(stats: Dict[str, Any]):
    """Sends overall category intelligence stats."""
    lines = [
        "📊 <b>DOODH KA HISAB - CATEGORY RADAR SUMMARY</b>",
        "",
        f"🔍 <b>Total Discovered Apps:</b> {stats.get('total_discovered', 0)}",
        f"⏳ <b>Pending in Discovery Queue:</b> {stats.get('pending_discovery', 0)}",
        f"🚀 <b>Actively Tracked Apps:</b> {stats.get('actively_tracked', 0)}",
        f"💬 <b>Total Reviews Logged:</b> {stats.get('total_reviews_captured', 0)}",
        f"🔄 <b>Total Updates Detected:</b> {stats.get('total_updates_detected', 0)}",
        "",
        "<i>All systems active and monitoring.</i>"
    ]
    send_telegram_message("\n".join(lines))

def test_telegram_connection() -> bool:
    """Sends a ping message to test credentials."""
    msg = (
        "🤖 <b>Telegram Alert System Connected!</b>\n\n"
        "Your <b>Doodh Ka Hisab Competitor Intelligence Bot</b> is successfully linked to this chat.\n"
        "You will receive alerts here whenever:\n"
        "• A competitor updates their app\n"
        "• A new user review is posted\n"
        "• Daily batch of new competitor apps are discovered"
    )
    return send_telegram_message(msg)
