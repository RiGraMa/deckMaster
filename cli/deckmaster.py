"""deckmaster.py"""


import csv
import os
import logging
import argparse

import db_collection
from edhrec import scrape_edhrec_average_deck, slugify_commander_name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
# NOTE: default keeps the original folder name (with typo) for compatibility.
CUSTOM_DECKLISTS_FOLDER = os.environ.get("DECKMASTER_CUSTOM_DECKLISTS", "costume DeckLists")
COMMANDERS_FOLDER       = os.environ.get("DECKMASTER_COMMANDERS_DIR", "commanders")
COLLECTION_FILE         = os.environ.get("DECKMASTER_COLLECTION_CSV", "collection.csv")

def create_folder_if_not_exists(folder_path):
    """Create a folder if it doesn't already exist."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logging.info(f"Created folder: {folder_path}")

def process_custom_decklist(decklist_path):
    """Process a custom decklist and compare it with the collection."""
    try:
        with open(decklist_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        # Extract the commander name from the first line
        commander_name = lines[0].split(" ", 1)[1].strip()
        formatted_name = commander_name.replace(",", "").replace("'", "").replace(" ", "-").lower()

        # Create a folder for the custom decklist with (Custom) suffix
        commander_folder = os.path.join(COMMANDERS_FOLDER, f"{formatted_name} (Custom)")
        create_folder_if_not_exists(commander_folder)

        # Prepare data for CSV
        rows = [line.strip().split(" ", 1) for line in lines if line.strip()]

        # Save the decklist to a CSV file
        csv_path = os.path.join(commander_folder, f"{formatted_name}.csv")
        with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Quantity", "Name"])  # Write header
            writer.writerows(rows)

        logging.info(f"Decklist saved to {csv_path}")

        # Compare with collection file (if it exists)
        if os.path.isfile(COLLECTION_FILE):
            logging.info("Collection file found. Comparing...")

            collection_dict = db_collection.load_collection_from_db()
            if not collection_dict:
                logging.warning("Could not load collection from database")
                return

            collection_cards = set(collection_dict.keys())  # Convert to set for comparison

            # Compare the decklist with the collection
            owned_cards = []
            not_owned_cards = []

            for row in rows:
                quantity, name = row
                card_name = name.strip().lower()
                if card_name in collection_cards:
                    owned_cards.append([quantity, name])
                else:
                    not_owned_cards.append([quantity, name])

            # Write owned cards to a CSV file
            with open(os.path.join(commander_folder, "owned_cards.csv"), mode="w", newline="", encoding="utf-8") as owned_file:
                writer = csv.writer(owned_file)
                writer.writerow(["Quantity", "Name"])
                writer.writerows(owned_cards)

            # Write not owned cards to a CSV file
            with open(os.path.join(commander_folder, "not_owned_cards.csv"), mode="w", newline="", encoding="utf-8") as not_owned_file:
                writer = csv.writer(not_owned_file)
                writer.writerow(["Quantity", "Name"])
                writer.writerows(not_owned_cards)

            logging.info("Comparison completed.")
            logging.info(f"Owned cards saved to {os.path.join(commander_folder, 'owned_cards.csv')}")
            logging.info(f"Not owned cards saved to {os.path.join(commander_folder, 'not_owned_cards.csv')}")
        else:
            logging.warning("Collection file not found.")

    except Exception as e:
        logging.error(f"An error occurred while processing the custom decklist: {e}")

def scrape_and_process_commander(commander_name):
    """
    Scrapes EDHREC data for a commander using JSON parsing.

    EDHREC stores data in __NEXT_DATA__ JSON (list or dict deck format).
    """
    formatted_name = slugify_commander_name(commander_name)

    # Create a directory for the commander with (EDHREC) suffix
    commander_folder = os.path.join(COMMANDERS_FOLDER, f"{formatted_name} (EDHREC)")
    create_folder_if_not_exists(commander_folder)

    try:
        rows, url = scrape_edhrec_average_deck(commander_name)
        logging.info(f"Fetching data from: {url}")
        logging.info(f"Found decklist with {len(rows)} cards")

        csv_path = os.path.join(commander_folder, f"{formatted_name}.csv")
        with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Quantity", "Name"])
            for row in rows:
                writer.writerow([row["quantity"], row["name"]])

        logging.info(f"Decklist saved to {csv_path}")

        # Compare with collection file (if it exists)
        if os.path.isfile(COLLECTION_FILE):
            logging.info("Collection file found. Comparing...")

            collection_cards = set()
            with open(COLLECTION_FILE, mode="r", newline="", encoding="utf-8") as collection_file:
                collection_reader = csv.reader(collection_file)
                next(collection_reader)  # Skip header
                for row in collection_reader:
                    if len(row) >= 7:  # Ensure row has enough columns
                        collection_cards.add(row[0].strip().lower())

            # Compare the decklist with the collection
            owned_cards = []
            not_owned_cards = []

            for row in rows:
                quantity = row["quantity"]
                name = row["name"]
                card_name = name.strip().lower()
                if card_name in collection_cards:
                    owned_cards.append([quantity, name])
                else:
                    not_owned_cards.append([quantity, name])

            # Write owned cards to a CSV file
            with open(os.path.join(commander_folder, "owned_cards.csv"), mode="w", newline="", encoding="utf-8") as owned_file:
                writer = csv.writer(owned_file)
                writer.writerow(["Quantity", "Name"])
                writer.writerows(owned_cards)

            # Write not owned cards to a CSV file
            with open(os.path.join(commander_folder, "not_owned_cards.csv"), mode="w", newline="", encoding="utf-8") as not_owned_file:
                writer = csv.writer(not_owned_file)
                writer.writerow(["Quantity", "Name"])
                writer.writerows(not_owned_cards)

            logging.info("Comparison completed.")
            logging.info(f"Owned cards saved to {os.path.join(commander_folder, 'owned_cards.csv')}")
            logging.info(f"Not owned cards saved to {os.path.join(commander_folder, 'not_owned_cards.csv')}")
        else:
            logging.warning("Collection file not found.")

    except ValueError as e:
        logging.error(f"Error scraping EDHREC: {e}")
        if os.path.exists(commander_folder) and not os.listdir(commander_folder):
            os.rmdir(commander_folder)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def display_custom_decklists():
    """Display all custom decklists in the folder and allow the user to select one."""
    if not os.path.exists(CUSTOM_DECKLISTS_FOLDER):
        logging.warning(f"No '{CUSTOM_DECKLISTS_FOLDER}' folder found.")
        return None

    decklists = [f for f in os.listdir(CUSTOM_DECKLISTS_FOLDER) if f.endswith(".txt")]
    if not decklists:
        logging.warning(f"No decklists found in '{CUSTOM_DECKLISTS_FOLDER}'.")
        return None

    print("Available custom decklists:")
    for i, decklist in enumerate(decklists, start=1):
        print(f"{i}. {decklist}")

    try:
        choice = int(input("Select a decklist by number: "))
        if 1 <= choice <= len(decklists):
            return os.path.join(CUSTOM_DECKLISTS_FOLDER, decklists[choice - 1])
        else:
            logging.error("Invalid selection.")
            return None
    except ValueError:
        logging.error("Invalid input. Please enter a number.")
        return None

def main_menu():
    """Display the main menu and handle user input."""
    while True:
        print("\nWelcome to the Decklist Processor!")
        print("1. Scrape from EDHREC")
        print("2. Use a custom decklist")
        print("3. Exit")
        choice = input("Select an option (1, 2, or 3): ").strip()

        if choice == "1":
            commander_name = input("Please enter the commander's name: ").strip()
            if not commander_name:
                logging.error("Commander's name cannot be empty.")
                continue
            scrape_and_process_commander(commander_name)
        elif choice == "2":
            decklist_path = display_custom_decklists()
            if decklist_path:
                process_custom_decklist(decklist_path)
        elif choice == "3":
            print("Exiting the program. Goodbye!")
            break
        else:
            logging.error("Invalid option selected.")


def main():
    """Handle command-line arguments and run the appropriate function."""
    parser = argparse.ArgumentParser(description="DeckMaster: A tool to compare Magic: The Gathering decklists.")
    parser.add_argument("--commander", help="Scrape a decklist from EDHREC for the given commander.")
    parser.add_argument("--custom", help="Use a custom decklist from the specified file.")
    args = parser.parse_args()

    if args.commander:
        # Scrape from EDHREC
        logging.info(f"Fetching decklist for commander: {args.commander}")
        scrape_and_process_commander(args.commander)
    elif args.custom:
        # Use a custom decklist
        logging.info(f"Using custom decklist from: {args.custom}")
        process_custom_decklist(args.custom)
    else:
        # No arguments provided, show the interactive menu
        main_menu()

if __name__ == "__main__":
    main()