import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dairy_tracker_config import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Initializes tables for competitor tracking, discovery, history, and reviews."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Pool of all discovered apps from search keywords
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovered_pool (
                app_id TEXT PRIMARY KEY,
                title TEXT,
                developer TEXT,
                score REAL,
                icon_url TEXT,
                search_keyword TEXT,
                status TEXT DEFAULT 'pending', -- 'pending', 'tracked', 'ignored'
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Actively tracked apps with full detailed metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_apps (
                app_id TEXT PRIMARY KEY,
                title TEXT,
                developer TEXT,
                score REAL,
                ratings_count INTEGER,
                reviews_count INTEGER,
                installs TEXT,
                version TEXT,
                last_updated TEXT,
                recent_changes TEXT,
                description TEXT,
                url TEXT,
                icon_url TEXT,
                first_tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. History of changes (version upgrade, changelog change, score shift)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT,
                change_type TEXT, -- 'VERSION_UPDATE', 'WHATS_NEW_CHANGE', 'SCORE_CHANGE', 'INSTALLS_CHANGE'
                old_value TEXT,
                new_value TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES tracked_apps(app_id)
            )
        """)
        
        # 4. User reviews tracking with full metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                app_id TEXT,
                user_name TEXT,
                score INTEGER,
                content TEXT,
                review_created_at TEXT,
                thumbs_up_count INTEGER DEFAULT 0,
                app_version TEXT DEFAULT '',
                developer_reply TEXT DEFAULT '',
                reply_date TEXT DEFAULT '',
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES tracked_apps(app_id)
            )
        """)
        
        # Check and add new columns if table existed from earlier run
        cursor.execute("PRAGMA table_info(reviews)")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        for col_name, col_type in [
            ("thumbs_up_count", "INTEGER DEFAULT 0"),
            ("app_version", "TEXT DEFAULT ''"),
            ("developer_reply", "TEXT DEFAULT ''"),
            ("reply_date", "TEXT DEFAULT ''")
        ]:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # 5. Tracking batch history (e.g. daily added)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_date DATE DEFAULT (DATE('now')),
                apps_added INTEGER,
                notes TEXT
            )
        """)
        
        conn.commit()

# --- Discovery Pool Helpers ---

def add_to_discovered_pool(apps: List[Dict[str, Any]], keyword: str) -> int:
    """Adds newly discovered apps to the pool if not already existing. Returns count of new apps."""
    new_count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for app in apps:
            app_id = app.get("appId") or app.get("app_id")
            if not app_id:
                continue
            cursor.execute("SELECT app_id FROM discovered_pool WHERE app_id = ?", (app_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO discovered_pool (app_id, title, developer, score, icon_url, search_keyword, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    app_id,
                    app.get("title", ""),
                    app.get("developer", ""),
                    app.get("score") or 0.0,
                    app.get("icon", ""),
                    keyword
                ))
                new_count += 1
        conn.commit()
    return new_count

def get_pending_apps_from_pool(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetches next batch of pending apps from the pool. If limit is None or <=0, fetches all."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if limit and limit > 0:
            cursor.execute("""
                SELECT app_id, title, developer, score, icon_url, search_keyword, discovered_at
                FROM discovered_pool
                WHERE status = 'pending'
                ORDER BY score DESC, discovered_at ASC
                LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT app_id, title, developer, score, icon_url, search_keyword, discovered_at
                FROM discovered_pool
                WHERE status = 'pending'
                ORDER BY score DESC, discovered_at ASC
            """)
        return [dict(row) for row in cursor.fetchall()]

def mark_as_tracked(app_id: str):
    """Marks an app as tracked in the discovery pool."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE discovered_pool SET status = 'tracked' WHERE app_id = ?", (app_id,))
        conn.commit()

# --- Tracked Apps Management ---

def upsert_tracked_app(app_data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Saves or updates app metadata.
    Returns:
      is_new: True if the app was just added to tracked_apps.
      changes: List of detected changes if it already existed.
    """
    app_id = app_data.get("appId") or app_data.get("app_id")
    changes = []
    is_new = False
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tracked_apps WHERE app_id = ?", (app_id,))
        existing = cursor.fetchone()
        
        now_str = datetime.datetime.now().isoformat()
        
        if existing is None:
            is_new = True
            cursor.execute("""
                INSERT INTO tracked_apps (
                    app_id, title, developer, score, ratings_count, reviews_count,
                    installs, version, last_updated, recent_changes, description,
                    url, icon_url, first_tracked_at, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app_id,
                app_data.get("title", ""),
                app_data.get("developer", ""),
                app_data.get("score", 0.0),
                app_data.get("ratings", 0),
                app_data.get("reviews", 0),
                str(app_data.get("installs", "0")),
                str(app_data.get("version", "N/A")),
                str(app_data.get("updated", "")),
                app_data.get("recentChanges", "") or "",
                app_data.get("description", "") or "",
                app_data.get("url", f"https://play.google.com/store/apps/details?id={app_id}"),
                app_data.get("icon", ""),
                now_str,
                now_str
            ))
            cursor.execute("UPDATE discovered_pool SET status = 'tracked' WHERE app_id = ?", (app_id,))
        else:
            # Check for version changes
            old_version = existing["version"]
            new_version = str(app_data.get("version", "N/A"))
            if old_version != new_version and new_version not in ("N/A", "None", ""):
                changes.append({
                    "type": "VERSION_UPDATE",
                    "old": old_version,
                    "new": new_version
                })
                
            # Check for changelog / recent changes
            old_changelog = (existing["recent_changes"] or "").strip()
            new_changelog = (app_data.get("recentChanges") or "").strip()
            if new_changelog and old_changelog != new_changelog:
                changes.append({
                    "type": "WHATS_NEW_CHANGE",
                    "old": old_changelog,
                    "new": new_changelog
                })
                
            # Check for score changes
            old_score = existing["score"]
            new_score = app_data.get("score")
            if new_score and abs(old_score - new_score) >= 0.1:
                changes.append({
                    "type": "SCORE_CHANGE",
                    "old": str(old_score),
                    "new": str(new_score)
                })

            # Check for install tier jumps
            old_installs = existing["installs"]
            new_installs = str(app_data.get("installs", ""))
            if new_installs and old_installs != new_installs:
                changes.append({
                    "type": "INSTALLS_CHANGE",
                    "old": old_installs,
                    "new": new_installs
                })

            # Save recorded changes
            for ch in changes:
                cursor.execute("""
                    INSERT INTO app_history (app_id, change_type, old_value, new_value)
                    VALUES (?, ?, ?, ?)
                """, (app_id, ch["type"], ch["old"], ch["new"]))
            
            # Update app record
            cursor.execute("""
                UPDATE tracked_apps SET
                    title = ?,
                    developer = ?,
                    score = ?,
                    ratings_count = ?,
                    reviews_count = ?,
                    installs = ?,
                    version = ?,
                    last_updated = ?,
                    recent_changes = ?,
                    url = ?,
                    icon_url = ?,
                    last_checked_at = ?
                WHERE app_id = ?
            """, (
                app_data.get("title", existing["title"]),
                app_data.get("developer", existing["developer"]),
                app_data.get("score", existing["score"]),
                app_data.get("ratings", existing["ratings_count"]),
                app_data.get("reviews", existing["reviews_count"]),
                str(app_data.get("installs", existing["installs"])),
                new_version,
                str(app_data.get("updated", existing["last_updated"])),
                new_changelog or existing["recent_changes"],
                app_data.get("url", existing["url"]),
                app_data.get("icon", existing["icon_url"]),
                now_str,
                app_id
            ))
            
        conn.commit()
    return is_new, changes

def get_all_tracked_apps() -> List[Dict[str, Any]]:
    """Returns all currently tracked apps."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tracked_apps ORDER BY ratings_count DESC")
        return [dict(row) for row in cursor.fetchall()]

# --- Review Helpers ---

def record_review_if_new(app_id: str, review: Dict[str, Any]) -> bool:
    """
    Inserts a review with full metadata if it hasn't been logged yet.
    Returns True if it was newly inserted, False if it was already known.
    """
    review_id = str(review.get("reviewId") or review.get("id") or "")
    if not review_id:
        return False
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT review_id FROM reviews WHERE review_id = ?", (review_id,))
        if cursor.fetchone() is not None:
            return False # Strict deduplication: never repeat
            
        cursor.execute("""
            INSERT INTO reviews (
                review_id, app_id, user_name, score, content,
                review_created_at, thumbs_up_count, app_version,
                developer_reply, reply_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            review_id,
            app_id,
            review.get("userName") or "Anonymous",
            review.get("score") or 0,
            review.get("content") or "",
            str(review.get("at") or ""),
            review.get("thumbsUpCount") or 0,
            str(review.get("reviewCreatedVersion") or ""),
            str(review.get("replyContent") or ""),
            str(review.get("repliedAt") or "")
        ))
        conn.commit()
    return True

# --- Analytics & Summary ---

def get_summary_stats() -> Dict[str, Any]:
    """Returns overview statistics of the discovery and tracking system."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM discovered_pool")
        total_discovered = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM discovered_pool WHERE status = 'pending'")
        total_pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tracked_apps")
        total_tracked = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM reviews")
        total_reviews = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM app_history")
        total_changes = cursor.fetchone()[0]
        
        return {
            "total_discovered": total_discovered,
            "pending_discovery": total_pending,
            "actively_tracked": total_tracked,
            "total_reviews_captured": total_reviews,
            "total_updates_detected": total_changes
        }
