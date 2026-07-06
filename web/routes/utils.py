"""
DeckMaster Web - Shared Utilities

Database helpers and Scryfall API calls shared across all blueprints.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
routes/utils.py
"""

import os
import sqlite3
import threading
import time
import requests
from flask import current_app

SCRYFALL_BY_ID   = "https://api.scryfall.com/cards/{}"
SCRYFALL_BY_NAME = "https://api.scryfall.com/cards/named?fuzzy={}"

HEADERS = {
    "User-Agent": "DeckMaster/1.0 (https://github.com/RiGraMa/deckMaster)",
    "Accept": "application/json"
}

# Scryfall asks for <=10 requests/second. Default 150ms between calls (~6.6/s).
SCRYFALL_MIN_INTERVAL = float(os.environ.get("SCRYFALL_MIN_INTERVAL", "0.15"))
SCRYFALL_MAX_RETRIES = int(os.environ.get("SCRYFALL_MAX_RETRIES", "3"))

_local_lock = threading.Lock()


def _scryfall_rate_file():
    """Shared timestamp file so multiple gunicorn workers coordinate rate limits."""
    if path := os.environ.get("SCRYFALL_RATE_FILE"):
        return path
    db_path = os.environ.get("COLLECTION_DB", "collection.db")
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), ".scryfall_rate")


def _wait_for_scryfall_slot():
    """Block until we're allowed to make another Scryfall API request."""
    rate_file = _scryfall_rate_file()

    with _local_lock:
        try:
            os.makedirs(os.path.dirname(rate_file), exist_ok=True)
            with open(rate_file, "a+", encoding="utf-8") as f:
                try:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                except (ImportError, AttributeError, OSError):
                    pass

                f.seek(0)
                raw = f.read().strip()
                last = float(raw) if raw else 0.0
                now = time.time()
                wait = SCRYFALL_MIN_INTERVAL - (now - last)
                if wait > 0:
                    time.sleep(wait)

                f.seek(0)
                f.truncate()
                f.write(str(time.time()))
                f.flush()

                try:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except (ImportError, AttributeError, OSError):
                    pass
        except OSError:
            time.sleep(SCRYFALL_MIN_INTERVAL)


# ── Database ──────────────────────────────────────────────────────────────────
def get_collection():
    """Return a dict of {card_name_lower: scryfall_id} from collection.db."""
    db_path = current_app.config["COLLECTION_DB"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name, scryfall_id FROM cards")
    rows = cur.fetchall()
    conn.close()
    return {row["name"].lower(): row["scryfall_id"] for row in rows}


def fetch_scryfall_image(scryfall_id=None, name=None):
    """
    Fetch card image URI from Scryfall.
    Tries by ID first, falls back to fuzzy name search.
    Returns image_uri string or None on failure.
    """
    if not scryfall_id and not name:
        return None

    urls = []
    if scryfall_id:
        urls.append(SCRYFALL_BY_ID.format(scryfall_id))
    if name:
        urls.append(SCRYFALL_BY_NAME.format(requests.utils.quote(name)))

    for url in urls:
        for attempt in range(SCRYFALL_MAX_RETRIES):
            try:
                _wait_for_scryfall_slot()
                resp = requests.get(url, headers=HEADERS, timeout=10)

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", SCRYFALL_MIN_INTERVAL * (2 ** attempt + 1)))
                    print(f"Scryfall 429 for {url}, waiting {retry_after:.1f}s (attempt {attempt + 1})")
                    time.sleep(retry_after)
                    continue

                if resp.status_code != 200:
                    print(f"Scryfall returned {resp.status_code} for {url}")
                    break

                data = resp.json()

                if "image_uris" in data:
                    return data["image_uris"].get("normal")
                if "card_faces" in data:
                    return data["card_faces"][0]["image_uris"].get("normal")

                break

            except Exception as e:
                print(f"Scryfall fetch failed for {url}: {e}")
                if attempt + 1 < SCRYFALL_MAX_RETRIES:
                    time.sleep(SCRYFALL_MIN_INTERVAL * (2 ** attempt + 1))
                break

    return None