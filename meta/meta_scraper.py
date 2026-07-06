"""
MTGTop8 Meta Scraper

Scrapes metagame data from MTGTop8.com for multiple formats.
Replaces MTGGoldfish scraper which blocked automated requests.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
meta_scraper.py
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
import re

logger = logging.getLogger(__name__)

BASE_URL          = "https://mtgtop8.com"
REQUEST_DELAY     = 2.0

# MTGTop8 format codes
SUPPORTED_FORMATS = ['pauper', 'modern', 'vintage', 'legacy', 'standard']
FORMAT_CODES = {
    'pauper':   'PAU',
    'modern':   'MO',
    'vintage':  'VI',
    'legacy':   'LE',
    'standard': 'ST',
}

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":         "https://mtgtop8.com"
}


# ── URL helpers ───────────────────────────────────────────────────────────────
def get_meta_url(format_name):
    """Generate MTGTop8 meta URL for a format."""
    code = FORMAT_CODES.get(format_name.lower())
    return f"{BASE_URL}/format?f={code}"


# ── Meta page scraping ────────────────────────────────────────────────────────
def scrape_meta_page(format_name, max_decks=50):
    """
    Scrape meta page for archetype breakdown.

    MTGTop8 shows archetypes with meta% under AGGRO / CONTROL / COMBO headers.

    Returns list of dicts:
        [{'name': str, 'archetype_url': str, 'meta_percent': float}, ...]
    """
    url = get_meta_url(format_name)
    logger.info(f"Scraping meta page: {url}")

    try:
        response = requests.get(url, timeout=30, headers=HEADERS)
        response.raise_for_status()

        soup  = BeautifulSoup(response.content, 'lxml')
        decks = []

        # Archetype links follow pattern /archetype?a=NUMBER
        archetype_links = soup.find_all('a', href=lambda x: x and '/archetype?' in x and 'a=' in x)

        for link in archetype_links:
            if len(decks) >= max_decks:
                break

            deck_name     = link.get_text(strip=True)
            archetype_url = link.get('href', '')

            # Skip empty names and duplicates
            if not deck_name or any(d['name'] == deck_name for d in decks):
                continue

            # Skip "Other - X" categories
            if deck_name.startswith('Other -'):
                continue

            if not archetype_url.startswith('http'):
                archetype_url = BASE_URL + archetype_url

            # Meta percentage is in the next sibling text node
            meta_percent = 0.0
            parent = link.find_parent('td') or link.find_parent('div')
            if parent:
                text = parent.get_text()
                percent_match = re.search(r'(\d+\.?\d*)\s*%', text)
                if percent_match:
                    meta_percent = float(percent_match.group(1))

            decks.append({
                'name':          deck_name,
                'archetype_url': archetype_url,
                'meta_percent':  meta_percent,
                'url':           archetype_url,
            })

        logger.info(f"Found {len(decks)} archetypes on meta page")
        return decks

    except Exception as e:
        logger.error(f"Error scraping meta page: {e}")
        return None


# ── Archetype page — get a sample deck URL ────────────────────────────────────
def get_sample_deck_from_archetype(archetype_url):
    """
    Get the most recent deck URL from an archetype page.

    MTGTop8 archetype pages list decks as:
        /event?e=EVENT_ID&d=DECK_ID&f=FORMAT

    Returns full URL string or None.
    """
    try:
        time.sleep(REQUEST_DELAY)

        response = requests.get(archetype_url, timeout=30, headers=HEADERS)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Find event/deck links — pattern: /event?e=NUMBER&d=NUMBER
        for link in soup.find_all('a', href=True):
            href = link['href']
            if re.search(r'/event\?e=\d+&d=\d+', href):
                deck_url = BASE_URL + href if not href.startswith('http') else href
                logger.debug(f"Found sample deck: {deck_url}")
                return deck_url

        logger.warning(f"No deck found for archetype: {archetype_url}")
        return None

    except Exception as e:
        logger.error(f"Error getting sample deck from archetype: {e}")
        return None


# ── Deck page — parse card list ───────────────────────────────────────────────
def download_deck_text(deck_url):
    """
    Parse card list directly from MTGTop8 deck page HTML.

    MTGTop8 deck pages show cards as plain text grouped by type:
        19 LANDS
        4 Drossforge Bridge
        ...
        SIDEBOARD
        2 Hydroblast

    Returns list of {name, quantity} dicts (mainboard only), or None.
    """
    try:
        time.sleep(REQUEST_DELAY)

        response = requests.get(deck_url, timeout=30, headers=HEADERS)
        response.raise_for_status()

        soup  = BeautifulSoup(response.content, 'lxml')
        cards = []

        # MTGTop8 deck content is in the page text — find the section
        # that starts with the land/creature/spell counts
        # Cards appear as "4 Card Name" after section headers like "19 LANDS"
        page_text = soup.get_text(separator='\n')

        in_sideboard  = False
        found_maindeck = False

        for line in page_text.split('\n'):
            line = line.strip()

            if not line:
                continue

            # Detect sideboard — stop collecting mainboard
            if line.upper() == 'SIDEBOARD':
                in_sideboard = True
                continue

            if in_sideboard:
                continue

            # Section headers like "19 LANDS", "13 CREATURES", "15 INSTANTS and SORC."
            # These have a number followed by all-caps text — skip them
            if re.match(r'^\d+\s+[A-Z\s\.]+$', line):
                found_maindeck = True
                continue

            # Card lines: "4 Drossforge Bridge"
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match and found_maindeck:
                quantity  = int(match.group(1))
                card_name = match.group(2).strip()

                # Skip obvious non-card lines
                if len(card_name) < 2 or card_name.isupper():
                    continue

                cards.append({
                    'quantity': quantity,
                    'name':     card_name
                })

        if cards:
            logger.debug(f"Parsed {len(cards)} mainboard cards from deck page")
            return cards

        logger.warning(f"No cards parsed from {deck_url}")
        return None

    except Exception as e:
        logger.error(f"Error parsing deck page: {e}")
        return None


# ── Per-deck orchestration ────────────────────────────────────────────────────
def scrape_deck_cards(deck_info):
    """
    Get full card list for a deck via its archetype page.

    Returns list of {name, quantity} dicts or None on failure.
    """
    archetype_url = deck_info.get('archetype_url')

    if not archetype_url:
        return None

    logger.debug(f"Processing archetype: {deck_info['name']}")

    deck_url = get_sample_deck_from_archetype(archetype_url)

    if not deck_url:
        logger.warning(f"No sample deck found for: {deck_info['name']}")
        return None

    return download_deck_text(deck_url)


# ── Main entry point ──────────────────────────────────────────────────────────
def scrape_format_meta(format_name, max_decks=50, include_cards=True):
    """
    Complete meta scrape for a format.

    Returns dict:
        {
            'format':     str,
            'deck_count': int,
            'decks':      list of deck dicts
        }
    or None on failure.
    """
    if format_name.lower() not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported format: {format_name}")
        return None

    logger.info(f"Starting MTGTop8 meta scrape for {format_name} (max {max_decks} decks)")

    decks = scrape_meta_page(format_name, max_decks)

    if not decks:
        logger.error("Failed to scrape meta page")
        return None

    if include_cards:
        logger.info(f"Scraping card lists for {len(decks)} archetypes...")

        for i, deck in enumerate(decks, 1):
            logger.info(f"Progress: {i}/{len(decks)} - {deck['name']}")

            cards         = scrape_deck_cards(deck)
            deck['cards'] = cards if cards else []

            if i % 10 == 0:
                logger.info(f"Checkpoint: {i}/{len(decks)} archetypes completed")

    return {
        'format':     format_name,
        'deck_count': len(decks),
        'decks':      decks
    }


# ── Public helpers ────────────────────────────────────────────────────────────
def validate_format(format_name):
    """Check if a format is supported."""
    return format_name.lower() in SUPPORTED_FORMATS


def get_supported_formats():
    """Return list of supported formats."""
    return SUPPORTED_FORMATS.copy()