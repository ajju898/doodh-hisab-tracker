import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "dairy_competitors.db"

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Monitoring & Discovery Settings
DAILY_NEW_APPS_LIMIT = int(os.getenv("DAILY_NEW_APPS_LIMIT", "10"))
MAX_REVIEWS_PER_CHECK = int(os.getenv("MAX_REVIEWS_PER_CHECK", "15"))
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "4"))

# Play Store Region & Language for Indian Market
PLAYSTORE_COUNTRY = "in"
PLAYSTORE_LANG = "en"

# Search keywords to find all "Doodh ka Hisab" / Dairy Apps in India
TARGET_KEYWORDS = [
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
    "milk customer ledger",
    "gwala dairy",
    "doodh hisab book",
]
