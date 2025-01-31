import requests
from bs4 import BeautifulSoup
import csv
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
    print(f"Fetching data from: {url}")

    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'lxml')

        # Use a CSS selector to locate the content
        content = soup.select("code")

        if content:
            # Extract the text from the first matching element
            content_text = content[0].get_text(strip=True)

            # Remove double quotes and process the content
            content_text = content_text.replace('"', '')
            if len(content_text) > 1:
                content_text = content_text[1:]

            # Prepare data for CSV
            rows = [line.split(' ', 1) for line in content_text.splitlines() if line.strip()]

            # Save the content to a CSV file
            csv_path = os.path.join(commander_folder, f"{formatted_name}.csv")
            with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Quantity", "Name"])  # Write header
                writer.writerows(rows)

            print(f"Content saved to {csv_path}")

            # Check for collection file and compare
            if os.path.isfile('collection.csv'):
                print("Collection file found. Comparing...")

                collection_cards = set()
                with open('collection.csv', mode='r', newline='', encoding='utf-8') as collection_file:
                    collection_reader = csv.reader(collection_file)
                    next(collection_reader)  # Skip header
                    for row in collection_reader:
                        if len(row) >= 7:  # Ensure row has enough columns
                            collection_cards.add(row[0].strip().lower())

                # Compare the web CSV content with the collection
                owned_cards = []
                not_owned_cards = []

                with open(csv_path, mode='r', newline='', encoding='utf-8') as web_file:
                    web_reader = csv.reader(web_file)
                    next(web_reader)  # Skip header
                    for row in web_reader:
                        if len(row) >= 2:
                            quantity, name = row
                            card_name = name.strip().lower()
                            if card_name in collection_cards:
                                owned_cards.append([quantity, name])
                            else:
                                not_owned_cards.append([quantity, name])

                # Write owned cards to a CSV file
                with open(os.path.join(commander_folder, 'owned_cards.csv'), mode='w', newline='', encoding='utf-8') as owned_file:
                    writer = csv.writer(owned_file)
                    writer.writerow(["Quantity", "Name"])
                    writer.writerows(owned_cards)

                # Write not owned cards to a CSV file
                with open(os.path.join(commander_folder, 'not_owned_cards.csv'), mode='w', newline='', encoding='utf-8') as not_owned_file:
                    writer = csv.writer(not_owned_file)
                    writer.writerow(["Quantity", "Name"])
                    writer.writerows(not_owned_cards)

                print("Comparison completed.")
                print(f"Owned cards saved to {os.path.join(commander_folder, 'owned_cards.csv')}")
                print(f"Not owned cards saved to {os.path.join(commander_folder, 'not_owned_cards.csv')}")
            else:
                print("Collection file not found.")

        else:
            print("Content not found using the CSS selector.")
            os.rmdir(commander_folder)  # Delete empty folder if no content

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        os.rmdir(commander_folder)  # Delete empty folder on error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    commander_name = input("Please enter the commander's name: ")
    scrape_and_process_commander(commander_name)
