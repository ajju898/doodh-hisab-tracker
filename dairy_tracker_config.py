import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "dairy_competitors.db"
CATEGORIES_FILE = BASE_DIR / "categories.json"

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Monitoring & Discovery Settings
DAILY_NEW_APPS_LIMIT = int(os.getenv("DAILY_NEW_APPS_LIMIT", "1000")) # Track all apps
ENABLE_REVIEW_SCRAPING = os.getenv("ENABLE_REVIEW_SCRAPING", "true").lower() in ("true", "1", "yes")
MAX_REVIEWS_PER_RUN = int(os.getenv("MAX_REVIEWS_PER_RUN", "500")) # Max 500 reviews per cycle
MAX_REVIEWS_PER_APP = int(os.getenv("MAX_REVIEWS_PER_APP", "30")) # Per app batch size
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "4"))

# Play Store Region & Language for Indian Market
PLAYSTORE_COUNTRY = "in"
PLAYSTORE_LANG = "en"

def load_categories():
    """Loads custom categories and their search keywords from categories.json."""
    if CATEGORIES_FILE.exists():
        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "dairy": {
            "name": "Doodh Ka Hisab (Dairy)",
            "icon": "🥛",
            "keywords": [
                "doodh ka hisab",
                "doodh diary",
                "milk record",
                "dairy milk ledger",
                "dairy hisab kitab",
                "daily milk record",
                "milk delivery tracker",
                "dairy management",
                "milk collection",
                "dairy farm management",
                "gwala dairy",
                "doodh hisab book"
            ]
        }
    }

CATEGORIES = load_categories()

# Flat list of keywords for backwards compatibility
TARGET_KEYWORDS = []
for cat_id, cat_info in CATEGORIES.items():
    TARGET_KEYWORDS.extend(cat_info.get("keywords", []))
