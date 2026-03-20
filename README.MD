# DeckMaster

DeckMaster is a Python-based toolkit for Magic: The Gathering players,
consisting of two independent tools:

- **DeckMaster**: Manage your EDH/Commander decklists, scrape EDHREC,
and compare against your personal collection
- **Meta Master**: Analyze the MTG metagame across multiple formats
(Pauper, Modern, Vintage) and check how your collection stacks up

This is a passion project where I explore different technologies and
techniques to solve real-world problems.

Repository: https://github.com/RiGraMa/deckMaster

---

## Project Structure
```
deckMaster/
├── deckmaster.py          # DeckMaster main program
├── meta_master.py         # Meta Master main program
├── db_collection.py       # Shared database connection module
├── meta_analyzer.py       # Meta analysis logic
├── meta_cache.py          # Meta data caching
├── meta_scraper.py        # MTGGoldfish scraper
├── migrate_csv_to_db.py   # One-time ManaBox CSV to SQLite migration
├── collection.csv         # ManaBox collection export (source)
├── collection.db          # SQLite collection database (generated)
├── requirements.txt       # Python dependencies
├── commanders/            # Generated commander data (git ignored)
├── costume DeckLists/     # Custom decklists (git ignored)
├── meta_cache/            # Cached meta data (git ignored)
└── meta_decks/            # Downloaded meta decklists (git ignored)
```

---

## Collection Setup

DeckMaster uses a SQLite database to store your card collection.
The collection is sourced from a ManaBox CSV export and must be
manually migrated using the provided script.

1. Export your collection from ManaBox as a CSV file
2. Replace `collection.csv` with your export
3. Run the migration script:
```
   python migrate_csv_to_db.py
```

This generates `collection.db` which is used by both DeckMaster
and Meta Master.

---

## DeckMaster

Manage your Commander/EDH decklists. Scrape average decklists from
EDHREC or use custom lists, and compare them against your collection
to see what you own and what you're missing.

### Installation

1. Clone this repository:
```
   git clone https://github.com/RiGraMa/deckMaster.git
   cd deckMaster
```

2. Install the required dependencies:
```
   pip install -r requirements.txt
```

### Usage

**Command-Line Interface (CLI)**

- Scrape a decklist from EDHREC:
```
   python deckmaster.py --commander "K'rrik, Son of Yawgmoth"
```

- Use a custom decklist:
```
   python deckmaster.py --custom "costume DeckLists/krrik-deck.txt"
```

- Interactive menu:
```
   python deckmaster.py
```

**Menu Options**

- Scrape from EDHREC:
   Enter a commander name to fetch and process their average decklist.
```
   Please enter the commander's name: K'rrik, Son of Yawgmoth
```

- Use a Custom Decklist:
   Select from your saved decklists in the costume DeckLists folder.
```
   Available custom decklists:
   1. krrik-deck.txt
   2. atraxa-deck.txt
   Select a decklist by number: 1
```

- Exit

---

## Meta Master

Analyze the MTG metagame across multiple formats. Downloads the top
meta decks from MTGGoldfish, caches them locally, and compares them
against your collection to show you how close you are to building
the best decks in the format.

### Usage
```
python meta_master.py
```

**Menu Options**

- Select a format (Pauper, Modern, Vintage)
- Choose to use cached data or download fresh data from MTGGoldfish
- Select how many top decks to analyze (recommended 50-100)
- View results showing your collection coverage per deck
- Export decklists for decks you're interested in

---

## Requirements

See `requirements.txt` for full dependencies. Key libraries:
- `requests` — HTTP scraping
- `beautifulsoup4` — HTML parsing
- `sqlite3` — Collection database (built into Python)

