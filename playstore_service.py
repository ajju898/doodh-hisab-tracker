import logging
from typing import List, Dict, Any, Optional
from dairy_tracker_config import PLAYSTORE_COUNTRY, PLAYSTORE_LANG, TARGET_KEYWORDS

logger = logging.getLogger(__name__)

# Try importing google_play_scraper
try:
    from google_play_scraper import app as g_app, search as g_search, reviews as g_reviews, Sort
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    logger.error("google-play-scraper is not installed. Run: pip install google-play-scraper")

def is_relevant_app(title: str, description: str = "") -> bool:
    """Checks whether an app is genuinely related to milk/dairy/doodh hisab."""
    keywords = [
        "doodh", "milk", "dairy", "dairies", "gwala", "hisab", "khata", 
        "cattle", "cow", "buffalo", "dairy farm", "fat", "snf", "ledger"
    ]
    combined = (title + " " + description).lower()
    return any(k in combined for k in keywords)

def search_playstore(keyword: str, n_hits: int = 50) -> List[Dict[str, Any]]:
    """Searches Google Play Store for a given keyword."""
    if not SCRAPER_AVAILABLE:
        raise RuntimeError("google-play-scraper is not installed. Please install it first.")
        
    try:
        results = g_search(
            keyword,
            lang=PLAYSTORE_LANG,
            country=PLAYSTORE_COUNTRY,
            n_hits=n_hits
        )
        filtered = []
        for item in results:
            title = item.get("title", "")
            app_id = item.get("appId", "")
            # Filter to ensure it belongs to dairy / milk / hisab category
            if is_relevant_app(title):
                filtered.append(item)
        return filtered
    except Exception as e:
        logger.error(f"Error searching keyword '{keyword}': {e}")
        return []

def fetch_full_app_details(app_id: str) -> Optional[Dict[str, Any]]:
    """Fetches complete metadata for a given app ID from Google Play Store."""
    if not SCRAPER_AVAILABLE:
        raise RuntimeError("google-play-scraper is not installed.")
        
    try:
        data = g_app(
            app_id,
            lang=PLAYSTORE_LANG,
            country=PLAYSTORE_COUNTRY
        )
        return data
    except Exception as e:
        logger.warning(f"Could not fetch details for {app_id} (might be delisted or region locked): {e}")
        return None

def fetch_latest_reviews(app_id: str, count: int = 15) -> List[Dict[str, Any]]:
    """Fetches the newest user reviews for an app."""
    if not SCRAPER_AVAILABLE:
        return []
        
    try:
        result, _ = g_reviews(
            app_id,
            lang=PLAYSTORE_LANG,
            country=PLAYSTORE_COUNTRY,
            sort=Sort.NEWEST,
            count=count
        )
        return result
    except Exception as e:
        logger.warning(f"Could not fetch reviews for {app_id}: {e}")
        return []
