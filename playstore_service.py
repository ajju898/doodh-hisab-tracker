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

def is_relevant_app(title: str, query: str = "", description: str = "") -> bool:
    """Checks whether an app is genuinely relevant to the searched query."""
    if not query:
        return True
    stop_words = {"the", "and", "for", "with", "app", "apps", "free", "best", "new", "top", "game", "games"}
    query_terms = [
        w.lower() for w in query.split()
        if (len(w) >= 2 or any(c.isdigit() for c in w)) and w.lower() not in stop_words
    ]
    
    if not query_terms:
        return True
        
    combined = (title + " " + description).lower()
    return any(term in combined for term in query_terms)

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
            desc = item.get("description", "") or item.get("summary", "")
            # Filter to ensure relevance to the specific category keyword
            if is_relevant_app(title, query=keyword, description=desc):
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

def fetch_latest_reviews(app_id: str, count: int = 15, score: Optional[int] = 1) -> List[Dict[str, Any]]:
    """Fetches the newest 1-star user reviews/complaints for an app."""
    if not SCRAPER_AVAILABLE:
        return []
        
    try:
        kwargs = {
            "lang": PLAYSTORE_LANG,
            "country": PLAYSTORE_COUNTRY,
            "sort": Sort.NEWEST,
            "count": count
        }
        if score is not None:
            kwargs["filter_score_with"] = score

        result, _ = g_reviews(app_id, **kwargs)
        if score is not None:
            result = [r for r in result if r.get("score") == score]
        return result
    except Exception as e:
        logger.warning(f"Could not fetch reviews for {app_id}: {e}")
        return []
