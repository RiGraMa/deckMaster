"""
DeckMaster Web - Commander Blueprint

Routes for scraping and managing commander decklists from EDHREC.
Scraper logic integrated from deckmaster.py.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
routes/commander.py
"""

import csv
import json
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, request, current_app, redirect, url_for

commander_bp = Blueprint("commander", __name__)


# ── Scraper ───────────────────────────────────────────────────────────────────
def _slugify_commander_name(name: str) -> str:
    name = (name or "").strip()
    name = name.replace(",", "").replace("'", "")
    name = re.sub(r"\s+", "-", name)
    return name.lower()


def scrape_edhrec_average_deck(commander_name: str):
    """
    Return (rows, url) where rows is list of dicts: [{quantity:int, name:str}, ...]
    Raises ValueError on expected scrape failures.
    """
    slug = _slugify_commander_name(commander_name)
    if not slug:
        raise ValueError("Commander name cannot be empty.")

    encoded = urllib.parse.quote(slug)
    url = f"https://edhrec.com/average-decks/{encoded}"

    resp = requests.get(url, timeout=20, headers={"User-Agent": "DeckMaster/1.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    next_data = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
    if not next_data or not next_data.string:
        raise ValueError("Could not find EDHREC deck data on the page.")

    try:
        data = json.loads(next_data.string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse EDHREC data ({e}).")

    page_data = data.get("props", {}).get("pageProps", {}).get("data", {})
    decklist = page_data.get("deck", [])
    if not decklist:
        raise ValueError("Decklist not found in EDHREC data (commander may be invalid).")

    rows = []
    for line in decklist:
        parts = str(line).split(" ", 1)
        if len(parts) != 2:
            continue
        qty_str, card_name = parts[0].strip(), parts[1].strip()
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 1
        if card_name:
            rows.append({"quantity": qty, "name": card_name})

    if not rows:
        raise ValueError("EDHREC returned an empty decklist.")

    return rows, url


def save_deck_to_commander_folder(commander_name: str, rows):
    """
    Persist decklist to commanders/ so it shows up in Collection view.
    Returns created commander folder name (relative to commanders dir).
    """
    slug = _slugify_commander_name(commander_name)
    commanders_dir = current_app.config["COMMANDERS_DIR"]
    folder_name = f"{slug} (EDHREC)"
    folder_path = os.path.join(commanders_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    csv_path = os.path.join(folder_path, f"{folder_name}.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Quantity", "Name"])
        for row in rows:
            writer.writerow([row["quantity"], row["name"]])

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