"""
DeckMaster Web - Collection Blueprint

Routes for browsing commander folders and viewing decklists
cross-referenced against the user's collection.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
routes/collection.py
"""

import os
import csv
from flask import Blueprint, render_template, jsonify, abort, request, current_app
from web.routes.utils import get_collection, fetch_scryfall_image

collection_bp = Blueprint("collection", __name__)


# ── Decklist parsing ──────────────────────────────────────────────────────────
def parse_decklist(commander_folder):
    """
    Parse decklist from a commander folder.
    Priority 1: file matching folder name (e.g. krrik-son-of-yawgmoth.csv)
    Priority 2: any .csv/.txt that isn't owned_cards or not_owned_cards
    Returns list of dicts: [{quantity, name}, ...]
    """
    commanders_dir = current_app.config["COMMANDERS_DIR"]
    folder_path = os.path.join(commanders_dir, commander_folder)
    cards = []

    SKIP_FILES = {"owned_cards.csv", "not_owned_cards.csv"}
    folder_name = os.path.basename(folder_path)
    target_file = None

    exact_match = f"{folder_name}.csv"
    if os.path.isfile(os.path.join(folder_path, exact_match)):
        target_file = exact_match
    else:
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


def format_decklist_text(cards):
    """Plain-text decklist: one 'quantity name' line per card."""
    return "\n".join(f"{card['quantity']} {card['name']}" for card in cards)


# ── Routes ────────────────────────────────────────────────────────────────────
@collection_bp.route("/")
def index():
    """Home: list all commander folders."""
    commanders_dir = current_app.config["COMMANDERS_DIR"]

    if not os.path.isdir(commanders_dir):
        abort(500, "commanders/ folder not found")

    folders = sorted([
        f for f in os.listdir(commanders_dir)
        if os.path.isdir(os.path.join(commanders_dir, f))
    ])
    return render_template("index.html", commanders=folders)


@collection_bp.route("/deck/<path:commander_folder>")
def deck(commander_folder):
    """Deck page: show owned/missing cards for a commander."""
    commanders_dir = current_app.config["COMMANDERS_DIR"]
    folder_path = os.path.join(commanders_dir, commander_folder)

    if not os.path.isdir(folder_path):
        abort(404, f"Commander folder '{commander_folder}' not found")

    decklist = parse_decklist(commander_folder)
    if not decklist:
        abort(404, "No decklist file found in this folder")

    collection = get_collection()
    owned   = []
    missing = []

    for card in decklist:
        name_lower  = card["name"].lower()
        scryfall_id = collection.get(name_lower)

        entry = {
            "name":        card["name"],
            "quantity":    card["quantity"],
            "scryfall_id": scryfall_id,
            "owned":       scryfall_id is not None,
        }

        if scryfall_id:
            owned.append(entry)
        else:
            missing.append(entry)

    return render_template(
        "deck.html",
        commander=commander_folder,
        owned=owned,
        missing=missing,
        decklist=decklist,
        decklist_text=format_decklist_text(decklist),
        missing_text=format_decklist_text(missing),
        total=sum(c["quantity"] for c in decklist),
        owned_count=sum(c["quantity"] for c in owned),
        missing_count=sum(c["quantity"] for c in missing),
    )


@collection_bp.route("/api/card-image")
def card_image():
    """
    Fetch a single card image from Scryfall.
    Query params: ?id=<scryfall_id> or ?name=<card_name>
    Returns JSON: {image_uri: "..."}
    """
    scryfall_id = request.args.get("id")
    name        = request.args.get("name")

    if not scryfall_id and not name:
        return jsonify({"error": "Provide ?id= or ?name="}), 400

    image_uri = fetch_scryfall_image(scryfall_id=scryfall_id, name=name)

    if image_uri:
        return jsonify({"image_uri": image_uri})
    return jsonify({"image_uri": None, "error": "Card not found"}), 404