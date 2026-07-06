"""
CSV to SQLite Migration Script for DeckMaster

Migrates collection.csv to collection.db with proper handling of:
- Foil status (normal/foil string → boolean)
- Scryfall ID for future web integration
- Database reset on each run (handles collection updates)

Author: Ricardo Martins
"""

import sqlite3
import csv
import os
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_FILE = os.environ.get("COLLECTION_DB", "collection.db")
CSV_FILE = os.environ.get("COLLECTION_CSV", "collection.csv")


def reset_database(db_path):
    """
    Delete existing database file to start fresh.
    
    Args:
        db_path (str): Path to database file
    """
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Deleted existing database: {db_path}")
        except Exception as e:
            logger.error(f"Error deleting database: {e}")
            raise
    else:
        logger.info("No existing database found, creating new one")


def create_database(db_path):
    """
    Create SQLite database with cards table and indexes.
    
    Essential fields only:
    - name: Card name
    - set_code: Set abbreviation (MRD, ZNR, etc.)
    - set_name: Full set name
    - quantity: How many owned
    - foil: Is it foil?
    - rarity: common/uncommon/rare/mythic
    - scryfall_id: For future API integration
    
    Args:
        db_path (str): Path to database file
        
    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            set_code TEXT,
            set_name TEXT,
            quantity INTEGER DEFAULT 1,
            foil BOOLEAN DEFAULT 0,
            rarity TEXT,
            scryfall_id TEXT
        )
    ''')
    
    # Create indexes for fast lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_name ON cards(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_set_code ON cards(set_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scryfall_id ON cards(scryfall_id)')
    
    conn.commit()
    logger.info("Database schema created successfully")
    
    return conn


def parse_foil_status(foil_string):
    """
    Convert CSV foil status to boolean.
    
    Args:
        foil_string (str): Either 'normal' or 'foil'
        
    Returns:
        int: 1 for foil, 0 for normal (SQLite boolean)
    """
    return 1 if foil_string.lower() == 'foil' else 0


def parse_boolean(bool_string):
    """
    Convert CSV boolean string to SQLite boolean.
    
    Args:
        bool_string (str): 'true' or 'false'
        
    Returns:
        int: 1 for true, 0 for false
    """
    return 1 if bool_string.lower() == 'true' else 0


def import_csv_to_db(csv_file, conn):
    """
    Import CSV collection into SQLite database.
    
    CSV Format (columns used):
    0: Name
    1: Set code
    2: Set name
    4: Foil (normal/foil)
    5: Rarity
    6: Quantity
    8: Scryfall ID
    
    Args:
        csv_file (str): Path to CSV file
        conn (sqlite3.Connection): Database connection
    """
    cursor = conn.cursor()
    imported_count = 0
    skipped_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            
            logger.info(f"CSV Header: {header}")
            logger.info("Starting import...")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                if len(row) < 9:
                    logger.warning(f"Row {row_num}: Skipped (insufficient columns: {len(row)})")
                    skipped_count += 1
                    continue
                
                try:
                    # Parse essential data only
                    name = row[0].strip()
                    set_code = row[1].strip()
                    set_name = row[2].strip()
                    foil = parse_foil_status(row[4])
                    rarity = row[5].strip().lower()
                    quantity = int(row[6])
                    scryfall_id = row[8].strip()
                    
                    # Insert into database
                    cursor.execute('''
                        INSERT INTO cards (
                            name, set_code, set_name, quantity, foil, rarity, scryfall_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        name,
                        set_code,
                        set_name,
                        quantity,
                        foil,
                        rarity,
                        scryfall_id
                    ))
                    
                    imported_count += 1
                    
                    if imported_count % 100 == 0:
                        logger.info(f"Imported {imported_count} cards...")
                    
                except Exception as e:
                    logger.error(f"Row {row_num}: Error importing card '{row[0]}': {e}")
                    skipped_count += 1
                    continue
        
        conn.commit()
        
        logger.info("="*70)
        logger.info(f"Import complete!")
        logger.info(f"Successfully imported: {imported_count} cards")
        if skipped_count > 0:
            logger.warning(f"Skipped: {skipped_count} rows (errors or invalid data)")
        logger.info("="*70)
        
        return imported_count
        
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
        raise
    except Exception as e:
        logger.error(f"Error during CSV import: {e}")
        raise


def verify_import(conn):
    """
    Verify the import by running some basic queries.
    
    Args:
        conn (sqlite3.Connection): Database connection
    """
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print(" DATABASE VERIFICATION")
    print("="*70)
    
    # Total cards
    cursor.execute("SELECT COUNT(*) FROM cards")
    total_cards = cursor.fetchone()[0]
    print(f"\nTotal card entries: {total_cards}")
    
    # Total quantity
    cursor.execute("SELECT SUM(quantity) FROM cards")
    total_quantity = cursor.fetchone()[0]
    print(f"Total card quantity: {total_quantity}")
    
    # Foils
    cursor.execute("SELECT COUNT(*) FROM cards WHERE foil = 1")
    foil_count = cursor.fetchone()[0]
    print(f"Foil cards: {foil_count}")
    
    # Unique cards
    cursor.execute("SELECT COUNT(DISTINCT name) FROM cards")
    unique_cards = cursor.fetchone()[0]
    print(f"Unique card names: {unique_cards}")
    
    # Top 5 sets by card count
    cursor.execute('''
        SELECT set_code, set_name, COUNT(*) as card_count, SUM(quantity) as total_qty
        FROM cards
        GROUP BY set_code
        ORDER BY total_qty DESC
        LIMIT 5
    ''')
    
    print("\nTop 5 Sets by Quantity:")
    for row in cursor.fetchall():
        set_code, set_name, card_count, total_qty = row
        print(f"  {set_code} ({set_name}): {card_count} unique cards, {total_qty} total")
    
    # Sample cards
    cursor.execute('''
        SELECT name, set_code, quantity, foil, rarity, scryfall_id 
        FROM cards 
        LIMIT 5
    ''')
    
    print("\nSample Cards:")
    for row in cursor.fetchall():
        name, set_code, quantity, foil, rarity, scryfall_id = row
        foil_status = "FOIL" if foil else "Normal"
        print(f"  {quantity}x {name} ({set_code}) - {rarity.upper()} - {foil_status}")
        print(f"     Scryfall: {scryfall_id}")
    
    print("\n" + "="*70)


def main(skip_confirm=False):
    """Main migration workflow."""
    print("\n" + "="*70)
    print(" DECKMASTER - CSV TO SQLITE MIGRATION")
    print("="*70)
    print()

    if not os.path.isfile(CSV_FILE):
        print(f"CSV file not found: {CSV_FILE}")
        return

    if not skip_confirm:
        # Ask user if they want to reset
        print("This will DELETE the existing database and recreate it from CSV.")
        print(f"Database: {DB_FILE}")
        print(f"CSV Source: {CSV_FILE}")
        print()

        choice = input("Continue? [y/N]: ").strip().lower()

        if choice not in ['y', 'yes']:
            print("Migration cancelled.")
            return

        print()
    
    try:
        # Reset database
        reset_database(DB_FILE)
        
        # Create fresh database
        conn = create_database(DB_FILE)
        
        # Import CSV
        imported = import_csv_to_db(CSV_FILE, conn)
        
        if imported > 0:
            # Verify import
            verify_import(conn)
        
        conn.close()
        
        print("\nMigration completed successfully!")
        print(f"Database saved to: {DB_FILE}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate ManaBox CSV export to SQLite")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    main(skip_confirm=args.yes)