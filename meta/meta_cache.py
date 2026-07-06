"""
Meta Cache Manager

Handles caching of MTGGoldfish meta data to minimize server requests
and improve performance. Caches are stored with timestamps for freshness tracking.

Author: Ricardo Martins
meta_cache.py
"""

import os
import json
from datetime import datetime, timedelta
import logging

# Configure module logger
logger = logging.getLogger(__name__)

# Constants
CACHE_DIR = "meta_cache"
DATE_FORMAT = "%Y-%m-%d"


def ensure_cache_directory():
    """
    Create cache directory if it doesn't exist.
    
    Returns:
        str: Path to cache directory
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        logger.info(f"Created cache directory: {CACHE_DIR}")
    return CACHE_DIR


def get_cache_filename(format_name):
    """
    Generate cache filename for a given format.
    
    Args:
        format_name (str): Format name (e.g., 'pauper', 'modern')
        
    Returns:
        str: Cache filename with today's date
        
    Example:
        >>> get_cache_filename('pauper')
        'pauper_2026-01-08.json'
    """
    today = datetime.now().strftime(DATE_FORMAT)
    return f"{format_name}_{today}.json"


def get_cache_path(format_name):
    """
    Get full path to cache file for a format.
    
    Args:
        format_name (str): Format name
        
    Returns:
        str: Full path to cache file
    """
    ensure_cache_directory()
    filename = get_cache_filename(format_name)
    return os.path.join(CACHE_DIR, filename)


def find_latest_cache(format_name):
    """
    Find the most recent cache file for a format.
    
    Args:
        format_name (str): Format name
        
    Returns:
        tuple: (filepath, date) or (None, None) if no cache exists
        
    Example:
        >>> find_latest_cache('pauper')
        ('meta_cache/pauper_2026-01-08.json', datetime(2026, 1, 8))
    """
    ensure_cache_directory()
    
    # Find all cache files for this format
    cache_files = []
    for filename in os.listdir(CACHE_DIR):
        if filename.startswith(format_name) and filename.endswith('.json'):
            # Extract date from filename
            try:
                date_str = filename.replace(format_name + '_', '').replace('.json', '')
                cache_date = datetime.strptime(date_str, DATE_FORMAT)
                filepath = os.path.join(CACHE_DIR, filename)
                cache_files.append((filepath, cache_date))
            except ValueError:
                # Invalid filename format, skip
                continue
    
    if not cache_files:
        return None, None
    
    # Return most recent cache
    latest = max(cache_files, key=lambda x: x[1])
    return latest


def load_cache(format_name):
    """
    Load cached meta data for a format.
    
    Args:
        format_name (str): Format name
        
    Returns:
        dict: Cached data with structure:
            {
                'format': str,
                'cached_date': str,
                'deck_count': int,
                'decks': list
            }
        None if no cache exists
    """
    filepath, cache_date = find_latest_cache(format_name)
    
    if not filepath:
        logger.info(f"No cache found for {format_name}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded cache for {format_name} from {cache_date.strftime(DATE_FORMAT)}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse cache file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
        return None


def save_cache(format_name, data):
    """
    Save meta data to cache with timestamp.
    
    Args:
        format_name (str): Format name
        data (dict): Meta data to cache (should include 'decks' list)
        
    Returns:
        bool: True if successful, False otherwise
    """
    ensure_cache_directory()
    
    # Add metadata
    cache_data = {
        'format': format_name,
        'cached_date': datetime.now().strftime(DATE_FORMAT),
        'deck_count': len(data.get('decks', [])),
        'decks': data.get('decks', [])
    }
    
    filepath = get_cache_path(format_name)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Saved cache for {format_name} ({cache_data['deck_count']} decks)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")
        return False


def get_cache_age_days(format_name):
    """
    Get age of cache in days.
    
    Args:
        format_name (str): Format name
        
    Returns:
        int: Days since cache was created, or None if no cache exists
    """
    filepath, cache_date = find_latest_cache(format_name)
    
    if not cache_date:
        return None
    
    age = datetime.now() - cache_date
    return age.days


def cache_exists(format_name):
    """
    Check if cache exists for a format.
    
    Args:
        format_name (str): Format name
        
    Returns:
        bool: True if cache exists, False otherwise
    """
    filepath, _ = find_latest_cache(format_name)
    return filepath is not None


def clear_old_caches(format_name, keep_latest=True):
    """
    Remove old cache files for a format.
    
    Args:
        format_name (str): Format name
        keep_latest (bool): If True, keep the most recent cache
        
    Returns:
        int: Number of files deleted
    """
    ensure_cache_directory()
    
    cache_files = []
    for filename in os.listdir(CACHE_DIR):
        if filename.startswith(format_name) and filename.endswith('.json'):
            try:
                date_str = filename.replace(format_name + '_', '').replace('.json', '')
                cache_date = datetime.strptime(date_str, DATE_FORMAT)
                filepath = os.path.join(CACHE_DIR, filename)
                cache_files.append((filepath, cache_date))
            except ValueError:
                continue
    
    if not cache_files:
        return 0
    
    # Sort by date (newest first)
    cache_files.sort(key=lambda x: x[1], reverse=True)
    
    # Determine which files to delete
    files_to_delete = cache_files[1:] if keep_latest else cache_files
    
    deleted_count = 0
    for filepath, _ in files_to_delete:
        try:
            os.remove(filepath)
            deleted_count += 1
            logger.info(f"Deleted old cache: {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Failed to delete {filepath}: {e}")
    
    return deleted_count


def get_cache_info(format_name):
    """
    Get information about cached data for display to user.
    
    Args:
        format_name (str): Format name
        
    Returns:
        dict: Cache information or None if no cache exists
            {
                'exists': bool,
                'date': str,
                'age_days': int,
                'deck_count': int
            }
    """
    if not cache_exists(format_name):
        return {
            'exists': False,
            'date': None,
            'age_days': None,
            'deck_count': 0
        }
    
    cache_data = load_cache(format_name)
    age_days = get_cache_age_days(format_name)
    
    return {
        'exists': True,
        'date': cache_data.get('cached_date', 'Unknown'),
        'age_days': age_days,
        'deck_count': cache_data.get('deck_count', 0)
    }