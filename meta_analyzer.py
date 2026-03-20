"""
Meta Deck Analyzer - FIXED VERSION

Properly handles card quantities in collection and deck comparison.

Author: Ricardo Martins
meta_analyzer.py
"""

import csv
import logging
import os
import db_collection 

logger = logging.getLogger(__name__)

LIKELY_BUILT_THRESHOLD = 0.95
DEFAULT_TOP_COUNT = 5


def load_collection(collection_file='collection.csv'):
    """Load from database instead of CSV."""
    return db_collection.load_collection_from_db()


def calculate_deck_completion(deck_cards, collection):
    """
    Calculate deck completion accounting for quantities.
    
    Args:
        deck_cards (list): List of dicts with 'name' and 'quantity'
        collection (dict): Dict mapping card names to quantities owned
        
    Returns:
        dict: Completion analysis
    """
    if not deck_cards:
        return {
            'total_cards': 0,
            'owned_cards': 0,
            'completion_percent': 0.0,
            'missing_cards': [],
            'owned_breakdown': []
        }
    
    total_cards = 0
    owned_cards = 0
    missing_cards = []
    owned_breakdown = []
    
    for card in deck_cards:
        card_name = card['name'].strip().lower()
        quantity_needed = card['quantity']
        
        total_cards += quantity_needed
        
        # Check how many copies we own
        quantity_owned = collection.get(card_name, 0)
        
        if quantity_owned > 0:
            # Count how many we can use (min of owned vs needed)
            usable_count = min(quantity_owned, quantity_needed)
            owned_cards += usable_count
            
            # Track what we own
            owned_breakdown.append({
                'name': card['name'],
                'quantity_needed': quantity_needed,
                'quantity_owned': quantity_owned,
                'quantity_usable': usable_count
            })
            
            # If we don't have enough, track shortage
            if quantity_owned < quantity_needed:
                missing_count = quantity_needed - quantity_owned
                missing_cards.append({
                    'name': card['name'],
                    'quantity': missing_count
                })
        else:
            # We don't own any copies
            missing_cards.append({
                'name': card['name'],
                'quantity': quantity_needed
            })
    
    completion_percent = (owned_cards / total_cards * 100) if total_cards > 0 else 0.0
    
    return {
        'total_cards': total_cards,
        'owned_cards': owned_cards,
        'completion_percent': completion_percent,
        'missing_cards': missing_cards,
        'owned_breakdown': owned_breakdown
    }


def analyze_decks(meta_data, collection_file='collection.csv'):
    """
    Analyze all meta decks against user collection.
    
    Args:
        meta_data (dict): Meta data from scraper with 'decks' list
        collection_file (str): Path to collection CSV
        
    Returns:
        list: Analyzed decks sorted by completion percentage
        None if analysis fails
    """
    collection = load_collection(collection_file)
    
    if collection is None:
        logger.error("Cannot analyze decks without collection")
        return None
    
    decks = meta_data.get('decks', [])
    
    if not decks:
        logger.warning("No decks to analyze")
        return []
    
    logger.info(f"Analyzing {len(decks)} decks against collection")
    
    analyzed_decks = []
    
    for deck in decks:
        deck_cards = deck.get('cards', [])
        
        if not deck_cards:
            logger.warning(f"Deck '{deck['name']}' has no cards, skipping")
            continue
        
        analysis = calculate_deck_completion(deck_cards, collection)
        
        completion = analysis['completion_percent']
        likely_built = completion >= (LIKELY_BUILT_THRESHOLD * 100)
        
        analyzed_deck = {
            'name': deck['name'],
            'meta_percent': deck.get('meta_percent', 0.0),
            'completion_percent': completion,
            'total_cards': analysis['total_cards'],
            'owned_cards': analysis['owned_cards'],
            'missing_cards': analysis['missing_cards'],
            'owned_breakdown': analysis['owned_breakdown'],
            'likely_built': likely_built
        }
        
        analyzed_decks.append(analyzed_deck)
    
    analyzed_decks.sort(key=lambda x: x['completion_percent'], reverse=True)
    
    logger.info(f"Analysis complete: {len(analyzed_decks)} decks analyzed")
    
    return analyzed_decks


def get_top_buildable_decks(analyzed_decks, count=DEFAULT_TOP_COUNT):
    """
    Get top buildable decks, ensuring enough non-built options.
    
    Args:
        analyzed_decks (list): List of analyzed decks
        count (int): Target number of buildable decks to show
        
    Returns:
        list: Top decks with enough non-built options
    """
    if not analyzed_decks:
        return []
    
    likely_built_in_top = 0
    for i, deck in enumerate(analyzed_decks):
        if i >= count + likely_built_in_top:
            break
        if deck['likely_built']:
            likely_built_in_top += 1
    
    total_to_show = count + likely_built_in_top
    
    return analyzed_decks[:total_to_show]


def format_deck_summary(deck, rank):
    """Format a single deck for display."""
    name = deck['name']
    completion = deck['completion_percent']
    owned = deck['owned_cards']
    total = deck['total_cards']
    meta = deck['meta_percent']
    likely_built = deck['likely_built']
    
    status = "[LIKELY BUILT]" if likely_built else ""
    
    line = f"  {rank}. {name} - {completion:.1f}% complete ({owned}/{total} cards)"
    
    if meta > 0:
        line += f" | Meta: {meta:.1f}%"
    
    if status:
        line += f" {status}"
    
    return line


def format_missing_cards(missing_cards, max_display=10):
    """Format missing cards list for display."""
    if not missing_cards:
        return "     None - deck is complete"
    
    lines = []
    total_missing = len(missing_cards)
    
    sorted_missing = sorted(missing_cards, key=lambda x: x['quantity'], reverse=True)
    
    for i, card in enumerate(sorted_missing[:max_display]):
        quantity = card['quantity']
        name = card['name']
        lines.append(f"     {quantity}x {name}")
    
    if total_missing > max_display:
        remaining = total_missing - max_display
        lines.append(f"     ... and {remaining} more cards")
    
    return "\n".join(lines)


def display_analysis_results(analyzed_decks, top_count=DEFAULT_TOP_COUNT, 
                            show_missing_for_top=10):
    """Display analysis results in a formatted, readable way."""
    if not analyzed_decks:
        print("\nNo decks could be analyzed.")
        return
    
    top_decks = get_top_buildable_decks(analyzed_decks, top_count)
    
    print("\n" + "="*70)
    print(" META ANALYSIS RESULTS")
    print("="*70)
    print()
    
    total_decks = len(analyzed_decks)
    likely_built_count = sum(1 for d in analyzed_decks if d['likely_built'])
    avg_completion = sum(d['completion_percent'] for d in analyzed_decks) / total_decks
    
    print(f"Total decks analyzed: {total_decks}")
    print(f"Average completion: {avg_completion:.1f}%")
    print(f"Likely already built: {likely_built_count}")
    print()
    print("-"*70)
    print()
    
    print(f"Top Buildable Decks (showing {len(top_decks)}):")
    print()
    
    for rank, deck in enumerate(top_decks, 1):
        print(format_deck_summary(deck, rank))
    
    print()
    print("-"*70)
    print()
    
    print(f"Missing Cards (Top {min(show_missing_for_top, len(top_decks))} Decks):")
    print()
    
    for i, deck in enumerate(top_decks[:show_missing_for_top], 1):
        print(f"  {i}. {deck['name']}:")
        print(format_missing_cards(deck['missing_cards']))
        print()
    
    print("="*70)


def export_deck_to_files(deck, analyzed_deck, format_name, collection_file='collection.csv'):
    """
    Export a deck to CSV files with proper quantity tracking.
    
    Creates folder structure and three CSV files.
    """
    deck_folder_name = deck['name'].replace('/', '-').replace(' ', '-').lower()
    deck_folder = os.path.join('meta_decks', format_name, deck_folder_name)
    
    os.makedirs(deck_folder, exist_ok=True)
    
    logger.info(f"Exporting deck to: {deck_folder}")
    
    # 1. Full decklist CSV
    csv_path = os.path.join(deck_folder, f"{deck_folder_name}.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity', 'Name'])
        for card in deck.get('cards', []):
            writer.writerow([card['quantity'], card['name']])
    
    logger.info(f"Wrote full decklist: {csv_path}")
    
    # 2. Owned cards CSV (using the analyzed breakdown)
    owned_path = os.path.join(deck_folder, 'owned_cards.csv')
    with open(owned_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity Needed', 'Quantity Owned', 'Name'])
        
        for item in analyzed_deck.get('owned_breakdown', []):
            writer.writerow([
                item['quantity_needed'],
                item['quantity_usable'],
                item['name']
            ])
    
    logger.info(f"Wrote owned cards: {owned_path}")
    
    # 3. Missing cards CSV
    missing_path = os.path.join(deck_folder, 'not_owned_cards.csv')
    with open(missing_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity', 'Name'])
        for card in analyzed_deck['missing_cards']:
            writer.writerow([card['quantity'], card['name']])
    
    logger.info(f"Wrote missing cards: {missing_path}")
    
    print()
    print("-"*70)
    print(f"Deck '{deck['name']}' exported successfully!")
    print()
    print(f"Location: {deck_folder}")
    print()
    print("Files created:")
    print(f"  1. {deck_folder_name}.csv - Full decklist ({analyzed_deck['total_cards']} cards)")
    print(f"  2. owned_cards.csv - Cards you own ({analyzed_deck['owned_cards']} cards)")
    print(f"  3. not_owned_cards.csv - Cards you need ({len(analyzed_deck['missing_cards'])} cards)")
    print("-"*70)


def offer_deck_export(analyzed_decks, meta_data, format_name):
    """Interactive prompt to export decks to CSV files."""
    if not analyzed_decks or not meta_data:
        return
    
    print()
    print("-"*70)
    print()
    print("Would you like to export any deck to CSV files?")
    print("(Creates folder with full decklist, owned cards, and missing cards)")
    print()
    
    choice = input("Export a deck? [y/N]: ").strip().lower()
    
    if choice not in ['y', 'yes']:
        return
    
    print()
    print("Available decks:")
    print()
    
    display_count = min(10, len(analyzed_decks))
    for i, deck in enumerate(analyzed_decks[:display_count], 1):
        status = "[LIKELY BUILT]" if deck['likely_built'] else ""
        print(f"  {i}. {deck['name']} - {deck['completion_percent']:.1f}% complete {status}")
    
    print()
    
    while True:
        deck_choice = input("Enter deck number to export (or 'done' to finish): ").strip()
        
        if deck_choice.lower() in ['done', '']:
            print("Export cancelled.")
            break
        
        try:
            idx = int(deck_choice) - 1
            
            if 0 <= idx < display_count:
                analyzed_deck = analyzed_decks[idx]
                
                original_deck = next(
                    (d for d in meta_data['decks'] if d['name'] == analyzed_deck['name']),
                    None
                )
                
                if original_deck and original_deck.get('cards'):
                    export_deck_to_files(original_deck, analyzed_deck, format_name)
                    
                    another = input("\nExport another deck? [y/N]: ").strip().lower()
                    if another not in ['y', 'yes']:
                        break
                else:
                    print(f"Error: Could not find card data for '{analyzed_deck['name']}'")
                    
            else:
                print(f"Please enter a number between 1 and {display_count}")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExport cancelled.")
            break