"""
DeckMaster Web - Visual Deck Browser
Flask app to visualize Commander decklists against your collection.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
app.py
"""

import os
import sqlite3
import csv
import requests
import time
from flask import Flask, render_template, jsonify, abort

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
COMMANDERS_DIR  = os.path.join(BASE_DIR, "commanders")
COLLECTION_DB   = os.path.join(BASE_DIR, "collection.db")
SCRYFALL_BY_ID  = "https://api.scryfall.com/cards/{}"
SCRYFALL_BY_NAME = "https://api.scryfall.com/cards/named?fuzzy={}"


# ── Database ──────────────────────────────────────────────────────────────────
def get_collection():
    """Return a dict of {card_name_lower: scryfall_id} from collection.db."""
    conn = sqlite3.connect(COLLECTION_DB)
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
            # Try fallback to name search if ID lookup failed
            if scryfall_id and name:
                return fetch_scryfall_image(name=name)
            return None

        data = resp.json()

        # Handle double-faced cards
        if "image_uris" in data:
            return data["image_uris"].get("normal")
        elif "card_faces" in data:
            return data["card_faces"][0]["image_uris"].get("normal")

        return None

    except Exception:
        return None


# ── Decklist parsing ──────────────────────────────────────────────────────────
def parse_decklist(commander_folder):
    """
    Parse decklist from a commander folder.
    Tries decklist.csv first, then falls back to any .csv or .txt file.
    Returns list of dicts: [{quantity, name}, ...]
    """
    folder_path = os.path.join(COMMANDERS_DIR, commander_folder)
    cards = []

    # Try to find decklist file
    # Priority 1: file matching folder name (e.g. krrik-son-of-yawgmoth.csv)
    # Priority 2: any .csv/.txt that isn't owned_cards or not_owned_cards
    SKIP_FILES = {"owned_cards.csv", "not_owned_cards.csv"}
    folder_name = os.path.basename(folder_path)

    target_file = None

    # Check for exact match first
    exact_match = f"{folder_name}.csv"
    if os.path.isfile(os.path.join(folder_path, exact_match)):
        target_file = exact_match
    else:
        # Fall back to any csv/txt that isn't an output file
        for filename in os.listdir(folder_path):
            if filename in SKIP_FILES:
                continue
            if filename.endswith(".csv") or filename.endswith(".txt"):
                target_file = filename
                break

    if not target_file:
        return cards

    filepath = os.path.join(folder_path, target_file)

    with open(filepath, newline="", encoding="utf-8") as f:
        # Detect if CSV or plain text (e.g. "1 Sol Ring")
        sample = f.read(512)
        f.seek(0)

        if "," in sample:
            reader = csv.DictReader(f)
            for row in reader:
                qty  = row.get("quantity") or row.get("Quantity") or row.get("qty") or "1"
                name = row.get("name")     or row.get("Name")     or row.get("card_name") or ""
                if name.strip():
                    cards.append({"quantity": int(qty.strip()), "name": name.strip()})
        else:
            # Plain text format: "1 Sol Ring" or "Sol Ring"
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(" ", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    cards.append({"quantity": int(parts[0]), "name": parts[1]})
                else:
                    cards.append({"quantity": 1, "name": line})

    return cards


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Home: list all commander folders."""
    if not os.path.isdir(COMMANDERS_DIR):
        abort(500, "commanders/ folder not found")

    folders = sorted([
        f for f in os.listdir(COMMANDERS_DIR)
        if os.path.isdir(os.path.join(COMMANDERS_DIR, f))
    ])
    return render_template("index.html", commanders=folders)


@app.route("/deck/<path:commander_folder>")
def deck(commander_folder):
    """Deck page: show owned/missing cards for a commander."""
    folder_path = os.path.join(COMMANDERS_DIR, commander_folder)
    if not os.path.isdir(folder_path):
        abort(404, f"Commander folder '{commander_folder}' not found")

    decklist = parse_decklist(commander_folder)
    if not decklist:
        abort(404, "No decklist file found in this folder")

    collection = get_collection()

    owned   = []
    missing = []

    for card in decklist:
        name_lower = card["name"].lower()
        scryfall_id = collection.get(name_lower)
        owned_qty = 1 if scryfall_id else 0

        entry = {
            "name":        card["name"],
            "quantity":    card["quantity"],
            "scryfall_id": scryfall_id,
            "owned":       owned_qty > 0,
        }

        if owned_qty > 0:
            owned.append(entry)
        else:
            missing.append(entry)

    return render_template(
        "deck.html",
        commander=commander_folder,
        owned=owned,
        missing=missing,
        total=sum(c["quantity"] for c in decklist),
        owned_count=sum(c["quantity"] for c in owned),
        missing_count=sum(c["quantity"] for c in missing),
    )


@app.route("/api/card-image")
def card_image():
    """
    API endpoint to fetch a single card image from Scryfall.
    Query params: ?id=<scryfall_id> or ?name=<card_name>
    Returns JSON: {image_uri: "..."}
    Called by the frontend JS to lazy-load images.
    """
    from flask import request
    scryfall_id = request.args.get("id")
    name        = request.args.get("name")

    if not scryfall_id and not name:
        return jsonify({"error": "Provide ?id= or ?name="}), 400

    # Respect Scryfall rate limit: 10 requests/second
    time.sleep(0.1)
    image_uri = fetch_scryfall_image(scryfall_id=scryfall_id, name=name)

    if image_uri:
        return jsonify({"image_uri": image_uri})
    return jsonify({"image_uri": None, "error": "Card not found"}), 404


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)