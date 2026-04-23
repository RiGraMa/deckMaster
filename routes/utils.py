"""
DeckMaster Web - Shared Utilities

Database helpers and Scryfall API calls shared across all blueprints.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
routes/utils.py
"""

import sqlite3
import time
import requests
from flask import current_app

SCRYFALL_BY_ID   = "https://api.scryfall.com/cards/{}"
SCRYFALL_BY_NAME = "https://api.scryfall.com/cards/named?fuzzy={}"


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


# ── Scryfall ──────────────────────────────────────────────────────────────────
def fetch_scryfall_image(scryfall_id=None, name=None):
    """
    Fetch card image URI from Scryfall.
    Tries by ID first, falls back to fuzzy name search.
    Returns image_uri string or None on failure.
    """
    try:
        if scryfall_id:
            url = SCRYFALL_BY_ID.format(scryfall_id)
        elif name:
            url = SCRYFALL_BY_NAME.format(requests.utils.quote(name))
        else:
            return None

        resp = requests.get(url, timeout=5)

        if resp.status_code != 200:
            if scryfall_id and name:
                return fetch_scryfall_image(name=name)
            return None

        data = resp.json()

        if "image_uris" in data:
            return data["image_uris"].get("normal")
        elif "card_faces" in data:
            return data["card_faces"][0]["image_uris"].get("normal")

        return None

    except Exception:
        return None