import requests
from bs4 import BeautifulSoup
import csv
from lxml import etree
import os
import urllib.parse

def scrape_and_process_commander(commander_name):
    """Scrapes EDHREC data for a commander, creates necessary folders, and generates CSV files.

    Args:
        commander_name (str): The name of the commander.
    """

    # URL encode the commander's name to handle special characters
    formatted_name = commander_name.replace(",", "").replace("'", "").replace(" ", "-").lower()
    encoded_name = urllib.parse.quote(formatted_name)

    # Create a directory for the commander (including "commanders" folder)
    commander_folder = os.path.join("commanders", formatted_name)

    # Create the folder if it doesn't exist
    os.makedirs(commander_folder, exist_ok=True)

    # Create the URL
    url = f"https://edhrec.com/average-decks/{encoded_name}"

    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for error HTTP statuses

        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'lxml')

        # Convert the BeautifulSoup object to an lxml object
        parser = etree.HTMLParser()
        tree = etree.fromstring(str(soup), parser)

        # Use XPath to find the specific element
        content = tree.xpath('/html/body/div[1]/main/div/div/div[1]/div[2]/div[2]/div/div[2]/div[2]/div/div[2]/div/div/code/text()')

        if content:
            # Join the content list into a single string
            content_text = ' '.join(content).strip()

            # Remove double quotes from the text
            content_text = content_text.replace('"', '')

            # Remove the first and last characters if the content is not empty
            if len(content_text) > 1:
                content_text = content_text[1:-1]

            # Prepare data for CSV
            rows = [line.split(' ', 1) for line in content_text.splitlines() if line.strip()]

            # Save the content to a CSV file
            with open(os.path.join(commander_folder, f"{formatted_name}.csv"), mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Write the header
                writer.writerow(["Quantity", "Name"])
                # Write the content rows
                writer.writerows(rows)

            print(f"Content saved to {os.path.join(commander_folder, f'{formatted_name}.csv')}")

            # Verify if the collection CSV exists and is readable
            if os.path.isfile('collection.csv'):
                print(f"Collection file found at collection.csv")

                collection_cards = set()
                try:
                    with open('collection.csv', mode='r', newline='', encoding='utf-8') as collection_file:
                        collection_reader = csv.reader(collection_file)
                        header = next(collection_reader)  # Skip the header row
                        for row in collection_reader:
                            if len(row) >= 7:  # Check if there are enough columns
                                name = row[0].strip().lower()  # Read the card name and normalize
                                collection_cards.add(name)
                except Exception as e:
                    print(f"Error reading collection file: {e}")
                    return

                # Compare the web CSV content with the collection
                owned_cards = []
                not_owned_cards = []

                try:
                    with open(os.path.join(commander_folder, f"{formatted_name}.csv"), mode='r', newline='', encoding='utf-8') as web_file:
                        web_reader = csv.reader(web_file)
                        header = next(web_reader)  # Skip the header row
                        for row in web_reader:
                            if len(row) >= 2:
                                quantity, name = row
                                card_name = name.strip().lower()

                                # Check for exact matches and matches against double-sided cards
                                match_found = False
                                for collection_card in collection_cards:
                                    if card_name == collection_card or card_name in collection_card:
                                        owned_cards.append([quantity, name])
                                        match_found = True
                                        break
                                if not match_found:
                                    not_owned_cards.append([quantity, name])
                except Exception as e:
                    print(f"Error reading web CSV file: {e}")
                    return

                # Write owned cards to a CSV file
                try:
                    with open(os.path.join(commander_folder, 'owned_cards.csv'), mode='w', newline='', encoding='utf-8') as owned_file:
                        writer = csv.writer(owned_file)
                        writer.writerow(["Quantity", "Name"])  # Header
                        writer.writerows(owned_cards)
                except Exception as e:
                    print(f"Error writing owned cards file: {e}")

                # Write not owned cards to a CSV file
                try:
                    with open(os.path.join(commander_folder, 'not_owned_cards.csv'), mode='w', newline='', encoding='utf-8') as not_owned_file:
                        writer = csv.writer(not_owned_file)
                        writer.writerow(["Quantity", "Name"])  # Header
                        writer.writerows(not_owned_cards)
                except Exception as e:
                    print(f"Error writing not owned cards file: {e}")

                print(f"Owned cards saved to {os.path.join(commander_folder, 'owned_cards.csv')}")
                print(f"Not owned cards saved to {os.path.join(commander_folder, 'not_owned_cards.csv')}")

            else:
                print(f"Collection file not found at collection.csv")

        else:
            print("Content not found using the provided XPath.")
            # Delete the empty folder
            try:
                os.rmdir(commander_folder)
                print(f"Empty folder {commander_folder} deleted.")
            except OSError as e:
                print(f"Error deleting folder: {e}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        # Delete the empty folder
        try:
            os.rmdir(commander_folder)
            print(f"Empty folder {commander_folder} deleted.")
        except OSError as e:
            print(f"Error deleting folder: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Consider logging the error or taking other actions

if __name__ == "__main__":
    commander_name = input("Please enter the commander's name: ")
    scrape_and_process_commander(commander_name)