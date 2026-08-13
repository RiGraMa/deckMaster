"""EDHREC average deck scraping helpers."""

import json
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


def slugify_commander_name(name: str) -> str:
    name = (name or "").strip()
    name = name.replace(",", "").replace("'", "")
    name = re.sub(r"\s+", "-", name)
    return name.lower()


def parse_edhrec_deck(deck_data):
    """
    Parse EDHREC deck field into rows: [{quantity: int, name: str}, ...]

    Supports the legacy list format ("1 Card Name") and the current dict format
    ({commander: [...], cards: {Type: [[name, qty], ...]}}).
    """
    rows = []

    if isinstance(deck_data, list):
        for line in deck_data:
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
    elif isinstance(deck_data, dict):
        for cmd in deck_data.get("commander") or []:
            name = str(cmd).strip()
            if name:
                rows.append({"quantity": 1, "name": name})

        cards = deck_data.get("cards") or {}
        if isinstance(cards, dict):
            for entries in cards.values():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                        continue
                    name = str(entry[0]).strip()
                    try:
                        qty = int(entry[1])
                    except (TypeError, ValueError):
                        qty = 1
                    if name:
                        rows.append({"quantity": qty, "name": name})

    return rows


def scrape_edhrec_average_deck(commander_name: str, *, timeout=20, user_agent="DeckMaster/1.0"):
    """
    Return (rows, url) where rows is list of dicts: [{quantity:int, name:str}, ...]
    Raises ValueError on expected scrape failures.
    """
    slug = slugify_commander_name(commander_name)
    if not slug:
        raise ValueError("Commander name cannot be empty.")

    encoded = urllib.parse.quote(slug)
    url = f"https://edhrec.com/average-decks/{encoded}"

    resp = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
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
    deck_data = page_data.get("deck")
    if not deck_data:
        raise ValueError("Decklist not found in EDHREC data (commander may be invalid).")

    rows = parse_edhrec_deck(deck_data)
    if not rows:
        raise ValueError("EDHREC returned an empty decklist.")

    return rows, url
