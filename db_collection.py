# db_collection.py - NEW FILE

import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_FILE = 'collection.db'

def load_collection_from_db(db_path=DB_FILE):
    """
    Load collection from SQLite database.
    
    Returns:
        dict: {card_name: total_quantity}
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Sum quantities for same card across different sets/printings
        cursor.execute('''
            SELECT LOWER(name), SUM(quantity)
            FROM cards
            GROUP BY LOWER(name)
        ''')
        
        collection = {}
        for name, quantity in cursor.fetchall():
            collection[name] = quantity
        
        conn.close()
        
        total_cards = sum(collection.values())
        logger.info(f"Loaded collection from DB: {len(collection)} unique cards ({total_cards} total)")
        return collection
        
    except Exception as e:
        logger.error(f"Error loading from database: {e}")
        return None