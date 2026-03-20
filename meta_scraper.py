"""
MTGGoldfish Meta Scraper - COMPLETELY REWRITTEN

Properly handles MTGGoldfish's archetype vs deck structure.

Author: Ricardo Martins
meta_scraper.py
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
import re

logger = logging.getLogger(__name__)

BASE_URL = "https://www.mtggoldfish.com"
SUPPORTED_FORMATS = ['pauper', 'modern', 'standard', 'vintage']
REQUEST_DELAY = 1.0


def get_meta_url(format_name):
    """Generate MTGGoldfish meta URL for a format."""
    return f"{BASE_URL}/metagame/{format_name}/full"


def scrape_meta_page(format_name, max_decks=50):
    """
    Scrape meta page for deck information.
    
    Returns list of deck dicts with 'name', 'archetype_url', and 'meta_percent'
    """
    url = get_meta_url(format_name)
    logger.info(f"Scraping meta page: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        decks = []
        
        # Find archetype links
        archetype_links = soup.find_all('a', href=lambda x: x and '/archetype/' in x)
        
        for link in archetype_links:
            if len(decks) >= max_decks:
                break
            
            deck_name = link.get_text(strip=True)
            archetype_url = link.get('href')
            
            if any(d['name'] == deck_name for d in decks):
                continue
            
            if archetype_url and not archetype_url.startswith('http'):
                archetype_url = BASE_URL + archetype_url
            
            # Get meta percentage
            meta_percent = 0.0
            parent = link.find_parent('div')
            if parent:
                percent_match = re.search(r'(\d+\.?\d*)\s*%', parent.get_text())
                if percent_match:
                    meta_percent = float(percent_match.group(1))
            
            decks.append({
                'name': deck_name,
                'archetype_url': archetype_url,
                'meta_percent': meta_percent
            })
        
        logger.info(f"Found {len(decks)} decks")
        return decks
        
    except Exception as e:
        logger.error(f"Error scraping meta page: {e}")
        return None


def get_sample_deck_from_archetype(archetype_url):
    """
    Get a specific deck URL from an archetype page.
    
    Archetype pages show the "average" deck but we need a real tournament deck.
    """
    try:
        time.sleep(REQUEST_DELAY)
        
        response = requests.get(archetype_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Look for links to specific decks in the "Similar Decks" section
        # These are /deck/{id} URLs
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Match pattern: /deck/NUMBER#online or /deck/NUMBER#paper
            if re.match(r'^/deck/\d+', href):
                deck_url = BASE_URL + href.split('#')[0]  # Remove #online/#paper
                logger.debug(f"Found sample deck: {deck_url}")
                return deck_url
        
        logger.warning(f"No sample deck found for {archetype_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting sample deck: {e}")
        return None


def download_deck_text(deck_url):
    """
    Download deck as text file from MTGGoldfish.
    
    Args:
        deck_url: URL to specific deck (not archetype)
    
    Returns:
        str: Deck text content
    """
    try:
        time.sleep(REQUEST_DELAY)
        
        # Convert deck URL to download URL
        # Pattern: /deck/12345 -> /deck/download/12345
        deck_id_match = re.search(r'/deck/(\d+)', deck_url)
        
        if not deck_id_match:
            logger.error(f"Could not extract deck ID from {deck_url}")
            return None
        
        deck_id = deck_id_match.group(1)
        download_url = f"{BASE_URL}/deck/download/{deck_id}"
        
        logger.debug(f"Downloading from: {download_url}")
        
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()
        
        return response.text
        
    except Exception as e:
        logger.error(f"Error downloading deck: {e}")
        return None


def parse_deck_text(deck_text):
    """
    Parse MTGGoldfish text format into card list.
    
    Format:
    Deck
    4 Lightning Bolt
    16 Mountain
    
    Sideboard
    3 Red Elemental Blast
    """
    if not deck_text:
        return []
    
    cards = []
    in_sideboard = False
    
    for line in deck_text.split('\n'):
        line = line.strip()
        
        if not line:
            continue
        
        # Check for sideboard marker
        if line.lower() == 'sideboard':
            in_sideboard = True
            continue
        
        # Skip other section headers
        if line.lower() in ['deck', 'creatures', 'spells', 'lands', 
                           'instants', 'sorceries', 'enchantments', 
                           'artifacts', 'planeswalkers']:
            continue
        
        # Skip sideboard cards
        if in_sideboard:
            continue
        
        # Parse card line: "4 Card Name"
        match = re.match(r'^(\d+)\s+(.+)$', line)
        if match:
            quantity = int(match.group(1))
            card_name = match.group(2).strip()
            
            cards.append({
                'name': card_name,
                'quantity': quantity
            })
    
    return cards


def scrape_deck_cards(deck_info):
    """
    Get card list for a deck (from archetype or specific deck).
    
    Args:
        deck_info: Dict with 'archetype_url'
    
    Returns:
        list: Card dicts with 'name' and 'quantity'
    """
    archetype_url = deck_info.get('archetype_url')
    
    if not archetype_url:
        return None
    
    logger.debug(f"Processing: {deck_info['name']}")
    
    # Get a sample deck from the archetype
    deck_url = get_sample_deck_from_archetype(archetype_url)
    
    if not deck_url:
        logger.warning(f"Could not find sample deck for {deck_info['name']}")
        return None
    
    # Download the deck text
    deck_text = download_deck_text(deck_url)
    
    if not deck_text:
        return None
    
    # Parse into cards
    cards = parse_deck_text(deck_text)
    
    logger.debug(f"Found {len(cards)} cards")
    return cards


def scrape_format_meta(format_name, max_decks=50, include_cards=True):
    """
    Complete meta scrape for a format.
    
    Returns dict with 'format', 'deck_count', and 'decks' list
    """
    if format_name not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported format: {format_name}")
        return None
    
    logger.info(f"Starting meta scrape for {format_name}")
    
    # Get meta page
    decks = scrape_meta_page(format_name, max_decks)
    
    if not decks:
        return None
    
    # Get card lists
    if include_cards:
        logger.info(f"Scraping card lists for {len(decks)} decks...")
        
        for i, deck in enumerate(decks, 1):
            logger.info(f"Progress: {i}/{len(decks)} - {deck['name']}")
            
            cards = scrape_deck_cards(deck)
            deck['cards'] = cards if cards else []
            deck['url'] = deck['archetype_url']  # For compatibility
            
            if i % 10 == 0:
                logger.info(f"Completed {i}/{len(decks)} decks")
    
    return {
        'format': format_name,
        'deck_count': len(decks),
        'decks': decks
    }


def validate_format(format_name):
    """Check if format is supported."""
    return format_name.lower() in SUPPORTED_FORMATS


def get_supported_formats():
    """Get list of supported formats."""
    return SUPPORTED_FORMATS.copy()