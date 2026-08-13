"""
DeckMaster Web - Commander Blueprint

Routes for scraping and managing commander decklists from EDHREC.
Scraper logic integrated from deckmaster.py.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
routes/commander.py
"""

import csv
import os

from flask import Blueprint, render_template, request, current_app, redirect, url_for

from edhrec import scrape_edhrec_average_deck, slugify_commander_name
from web.routes.utils import get_collection

commander_bp = Blueprint("commander", __name__)


def save_deck_to_commander_folder(commander_name: str, rows):
    """
    Persist decklist to commanders/ so it shows up in Collection view.
    Writes full decklist plus owned/not-owned splits when collection exists.
    Returns created commander folder name (relative to commanders dir).
    """
    slug = slugify_commander_name(commander_name)
    commanders_dir = current_app.config["COMMANDERS_DIR"]
    folder_name = f"{slug} (EDHREC)"
    folder_path = os.path.join(commanders_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    csv_path = os.path.join(folder_path, f"{slug}.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Quantity", "Name"])
        for row in rows:
            writer.writerow([row["quantity"], row["name"]])

    collection = get_collection()
    if collection:
        owned_cards = []
        not_owned_cards = []

        for row in rows:
            card_name = row["name"].strip().lower()
            line = [row["quantity"], row["name"]]
            if card_name in collection:
                owned_cards.append(line)
            else:
                not_owned_cards.append(line)

        for filename, card_rows in (
            ("owned_cards.csv", owned_cards),
            ("not_owned_cards.csv", not_owned_cards),
        ):
            with open(os.path.join(folder_path, filename), mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Quantity", "Name"])
                writer.writerows(card_rows)

    return folder_name


# ── Routes ────────────────────────────────────────────────────────────────────
@commander_bp.route("/scrape")
def scrape():
    """
    Scrape a commander decklist from EDHREC.
    """
    return render_template("commander.html")


@commander_bp.route("/scrape", methods=["POST"])
def scrape_post():
    commander_name = (request.form.get("commander_name") or "").strip()
    try:
        rows, url = scrape_edhrec_average_deck(commander_name)
        folder_name = save_deck_to_commander_folder(commander_name, rows)
        return redirect(url_for("collection.deck", commander_folder=folder_name))
    except Exception as e:
        return render_template(
            "commander.html",
            error=str(e),
            commander_name=commander_name,
        )