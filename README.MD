# DeckMaster

DeckMaster is a Python-based tool designed to help Magic: The Gathering players manage their EDH (Elder Dragon Highlander) decklists. It allows users to scrape decklists from EDHREC, compare them against their personal collection, and generate detailed reports of owned and missing cards.

This project is a passion project where I explore different technologies and techniques to solve real-world problems. It’s a great way for me to experiment with new ideas and improve my skills as a developer.

---

## Features

- **Scrape Decklists from EDHREC**: Fetch the average decklist for any commander.
- **Custom Decklists**: Process custom decklists stored in text files.
- **Collection Comparison**: Compare decklists against your personal collection to identify owned and missing cards.
- **Command-Line Interface (CLI)**: Run the tool with commands for faster and more efficient usage.
- **Interactive Menu**: User-friendly menu for those who prefer step-by-step guidance.

---

## Installation

1. Clone this repository:
   git clone https://github.com/RiGraMa/deckMaster.git
   cd deckMaster

2. Install the required dependencies:
   pip install -r requirements.txt


## Usage

DeckMaster can be used in two ways: via the Command-Line Interface (CLI) or the Interactive Menu.

**Command-Line Interface (CLI)**

-Scrape a Decklist from EDHREC
   To fetch and process a decklist for a specific commander, use the --commander argument:
   python deckmaster.py --commander "K'rrik, Son of Yawgmoth"

-Use a Custom Decklist
   To process a custom decklist from a file, use the --custom argument:
   python deckmaster.py --custom "costume DeckLists/krrik-deck.txt"

-Interactive Menu
   If no arguments are provided, the program will launch an interactive menu:
   python deckmaster.py

**Menu Options**
-Scrape from EDHREC:
   Enter the commander’s name to fetch and process their decklist.
   Example:
   Please enter the commander's name: K'rrik, Son of Yawgmoth

-Use a Custom Decklist:
   Select a custom decklist from the costume DeckLists folder.
   Example:
   Available custom decklists:
   1. krrik-deck.txt
   2. atraxa-deck.txt
   Select a decklist by number: 1

-Exit:
   Exit the program.


## Folder Structure
   commanders/: Contains folders for each commander, with CSV files for the decklist, owned cards, and not-owned cards.

   costume DeckLists/: Store your custom decklists here as .txt files.

   collection.csv: Your personal card collection. Ensure it follows the required format.