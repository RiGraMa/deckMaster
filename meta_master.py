"""
Meta Master - MTG Meta Analyzer

Master orchestrator for analyzing Magic: The Gathering metagames
against user card collection. Coordinates scraping, caching, and analysis.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
meta_master.py
"""

import logging
import sys

# Import our modules
import meta_cache
import meta_scraper
import meta_analyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def display_header():
    """Display program header."""
    print()
    print("="*70)
    print(" DECKMASTER - META ANALYZER")
    print("="*70)
    print()


def display_formats():
    """Display available formats and get user selection."""
    formats = meta_scraper.get_supported_formats()
    
    print("Select a format to analyze:")
    print()
    
    for i, format_name in enumerate(formats, 1):
        print(f"  {i}. {format_name.capitalize()}")
    
    print(f"  {len(formats) + 1}. Exit")
    print()
    
    while True:
        try:
            choice = input("Your choice: ").strip()
            choice_num = int(choice)
            
            if choice_num == len(formats) + 1:
                return None
            
            if 1 <= choice_num <= len(formats):
                return formats[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(formats) + 1}")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return None


def display_cache_status(format_name):
    """Display cache status and ask user if they want to update."""
    cache_info = meta_cache.get_cache_info(format_name)
    
    if not cache_info['exists']:
        print(f"\nNo cached data found for {format_name}.")
        print("Fresh data will be downloaded from MTGGoldfish.")
        return False
    
    print()
    print("-"*70)
    print(f"Cache Status for {format_name.capitalize()}:")
    print(f"  Last updated: {cache_info['date']}")
    print(f"  Age: {cache_info['age_days']} day(s) ago")
    print(f"  Contains: {cache_info['deck_count']} decks")
    print("-"*70)
    print()
    
    while True:
        choice = input("Use cached data? [Y/n]: ").strip().lower()
        
        if choice in ['', 'y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no")


def get_deck_limit():
    """Ask user how many decks to analyze."""
    print()
    print("How many top meta decks would you like to analyze?")
    print("  (Recommended: 50-100, more decks = longer download time)")
    print()
    
    while True:
        try:
            choice = input("Number of decks [default: 50]: ").strip()
            
            if choice == '':
                return 50
            
            deck_count = int(choice)
            
            if deck_count < 1:
                print("Please enter a positive number")
                continue
            
            if deck_count > 100:
                confirm = input(f"{deck_count} decks may take a while. Continue? [Y/n]: ")
                if confirm.lower() in ['n', 'no']:
                    continue
            
            return deck_count
            
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return None


def scrape_fresh_data(format_name, max_decks):
    """Scrape fresh meta data from MTGGoldfish."""
    print()
    print("="*70)
    print(f" DOWNLOADING {format_name.upper()} META DATA")
    print("="*70)
    print()
    print(f"Fetching top {max_decks} decks from MTGGoldfish...")
    print("This may take a few minutes depending on deck count.")
    print()
    
    meta_data = meta_scraper.scrape_format_meta(
        format_name, 
        max_decks=max_decks, 
        include_cards=True
    )
    
    if not meta_data:
        logger.error("Failed to scrape meta data")
        return None
    
    # Save to cache
    print()
    print("Saving to cache...")
    
    if meta_cache.save_cache(format_name, meta_data):
        print(f"Cache saved successfully: {format_name}")
        # Clean up old caches
        deleted = meta_cache.clear_old_caches(format_name, keep_latest=True)
        if deleted > 0:
            print(f"Cleaned up {deleted} old cache file(s)")
    else:
        logger.warning("Failed to save cache, but continuing with analysis")
    
    return meta_data


def analyze_format(format_name):
    """Complete analysis workflow for a format."""
    print()
    print("="*70)
    print(f" ANALYZING {format_name.upper()} META")
    print("="*70)
    
    # Check cache status
    use_cache = display_cache_status(format_name)
    
    meta_data = None
    
    if use_cache:
        # Load from cache
        print("\nLoading data from cache...")
        meta_data = meta_cache.load_cache(format_name)
        
        if not meta_data:
            logger.error("Failed to load cache, will download fresh data")
            use_cache = False
    
    if not use_cache:
        # Get deck limit from user
        max_decks = get_deck_limit()
        
        if max_decks is None:
            return
        
        # Scrape fresh data
        meta_data = scrape_fresh_data(format_name, max_decks)
        
        if not meta_data:
            print("\nFailed to download meta data. Please try again later.")
            return
    
    # Analyze against collection
    print()
    print("="*70)
    print(" ANALYZING AGAINST YOUR COLLECTION")
    print("="*70)
    print()
    
    analyzed_decks = meta_analyzer.analyze_decks(meta_data)
    
    if not analyzed_decks:
        print("\nFailed to analyze decks against collection.")
        print("Ensure collection.csv exists and is properly formatted.")
        return
    
    # Display results
    meta_analyzer.display_analysis_results(
        analyzed_decks,
        top_count=5,
        show_missing_for_top=10
    )

    meta_analyzer.offer_deck_export(analyzed_decks, meta_data, format_name)


def main_menu():
    """Main program loop."""
    display_header()
    
    while True:
        print()
        format_name = display_formats()
        
        if format_name is None:
            print("\nExiting. Thank you for using DeckMaster!")
            break
        
        try:
            analyze_format(format_name)
            
            # Ask if user wants to analyze another format
            print()
            choice = input("Analyze another format? [Y/n]: ").strip().lower()
            
            if choice in ['n', 'no']:
                print("\nThank you for using DeckMaster!")
                break
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            print("Thank you for using DeckMaster!")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            print("\nAn error occurred. Please check the logs.")


def main():
    """Entry point for the program."""
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



if __name__ == "__main__":
    main()