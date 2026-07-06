# DeckMaster — personal project notes

Passion project for managing my MTG collection and comparing it against Commander decks.
Not really written for an audience — this is my reference so I can pick the project back up
after months away without re-learning everything.

Repo: https://github.com/RiGraMa/deckMaster

---

## What this project does (high level)

Three loosely connected tools sharing one collection database:

| Tool | What it does | Status |
|------|----------------|--------|
| **Web app** | Browse scraped commander decks, see owned vs missing cards with Scryfall images, scrape EDHREC from browser, copy/download decklists | **Main tool — works** |
| **DeckMaster CLI** | Same EDHREC scraping + custom decklist processing from terminal | Works, but web is nicer now |
| **Meta Master** | Scrape Pauper/Modern/etc meta decks, compare vs collection, export lists | **Broken / abandoned for now** — kept in `meta/` |

The core idea everywhere: **take a decklist → compare card names against my ManaBox collection → show what I own and what I'm missing.**

---

## Project structure (after reorg, Jul 2026)

```
deckMaster/
├── app.py                      # Web entrypoint wrapper → imports web.app
├── deckmaster.py               # CLI entrypoint wrapper → cli/deckmaster.py
├── meta_master.py              # Meta entrypoint wrapper → meta/meta_master.py
├── migrate_csv_to_db.py        # Migration wrapper → collection_tools/
├── db_collection.py              # DB loader wrapper → collection_tools/
│
├── web/                        # Flask web application (the thing I actually use)
│   ├── app.py                  # create_app(), config, blueprint registration
│   ├── routes/
│   │   ├── collection.py       # Home, deck view, card image API, export text
│   │   ├── commander.py        # EDHREC scrape route + save deck files
│   │   └── utils.py            # SQLite collection lookup + Scryfall API
│   ├── templates/              # Jinja2 HTML
│   └── static/style.css        # Dark/gold MTG-ish theme
│
├── cli/
│   └── deckmaster.py           # Original CLI — EDHREC scrape + custom decklists
│
├── meta/                       # Meta Master — all meta files kept together even if broken
│   ├── meta_master.py          # Interactive menu orchestrator
│   ├── meta_scraper.py         # MTGTop8 scraper (was MTGGoldfish, got blocked)
│   ├── meta_cache.py           # JSON cache in meta_cache/
│   └── meta_analyzer.py        # Deck completion % + CSV export to meta_decks/
│
├── collection_tools/
│   ├── migrate_csv_to_db.py    # ManaBox CSV → SQLite
│   └── db_collection.py        # load_collection_from_db() for CLI/meta
│
├── data/                       # Docker persistent volume (gitignored contents)
│   ├── collection.csv          # My ManaBox export goes here when using Docker
│   ├── collection.db           # Auto-generated on first docker up
│   └── commanders/             # Scraped decks when using Docker
│
├── commanders/                 # Scraped decks when running locally (gitignored)
├── costume DeckLists/          # Custom deck .txt files (gitignored, typo kept for legacy)
├── meta_cache/                 # Cached meta JSON (gitignored)
├── meta_decks/                 # Exported meta deck CSVs (gitignored)
│
├── collection.csv              # Legacy local path for ManaBox export (repo root)
├── collection.db               # Legacy local path for SQLite DB (repo root)
│
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh
├── requirements.txt
└── README.MD                   # This file
```

**Why wrappers at root?** So old commands still work (`python deckmaster.py`, `gunicorn app:app`)
without remembering package paths. Real code lives in subfolders.

---

## Collection — the shared data layer

### Source: ManaBox CSV export

Export from ManaBox → save as CSV. Columns the migration script actually reads:

| Index | Column | Used for |
|-------|--------|----------|
| 0 | Name | Card name |
| 1 | Set code | e.g. ZNR |
| 2 | Set name | e.g. Zendikar Rising |
| 4 | Foil | `normal` or `foil` → boolean |
| 5 | Rarity | common/uncommon/rare/mythic |
| 6 | Quantity | How many I own |
| 8 | Scryfall ID | Used by web app for card images |

Example header from my export:
```
Name,Set code,Set name,Collector number,Foil,Rarity,Quantity,ManaBox ID,Scryfall ID,...
```

### Target: SQLite `collection.db`

Schema (`collection_tools/migrate_csv_to_db.py`):
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    set_code TEXT,
    set_name TEXT,
    quantity INTEGER DEFAULT 1,
    foil BOOLEAN DEFAULT 0,
    rarity TEXT,
    scryfall_id TEXT
);
```

Indexes on `name`, `set_code`, `scryfall_id`.

**Important:** Migration **deletes and recreates** the DB every run. It's not incremental.

### How each tool reads the collection

| Tool | How it checks ownership | Notes |
|------|-------------------------|-------|
| Web app | `get_collection()` → `{name_lower: scryfall_id}` | Only checks if card **exists** in DB, not quantity |
| CLI (custom deck) | `db_collection.load_collection_from_db()` → `{name_lower: total_qty}` | Sums quantities across printings |
| CLI (EDHREC scrape) | Still reads **`collection.csv` directly** (old code path) | Inconsistent with web — should migrate to DB |
| Meta analyzer | `db_collection.load_collection_from_db()` | Proper quantity-aware comparison |

### Migration commands

**Local (repo root):**
```bash
# interactive — asks for confirmation
python migrate_csv_to_db.py

# non-interactive (Docker / scripts)
python migrate_csv_to_db.py --yes
```

**Docker:**
```bash
# auto-runs on first `docker compose up` if data/collection.csv exists but no .db
docker compose up --build

# manual re-import after updating CSV
docker compose run --rm web python migrate_csv_to_db.py --yes
```

### Path config (env vars)

| Variable | Default (local) | Docker default |
|----------|-----------------|----------------|
| `COLLECTION_DB` | `./collection.db` | `/app/data/collection.db` |
| `COLLECTION_CSV` | `./collection.csv` | `/app/data/collection.csv` |
| `COMMANDERS_DIR` | `./commanders` | `/app/data/commanders` |

---

## Commander decks — folder layout & file formats

When I scrape a commander (web or CLI), a folder is created:

```
commanders/
└── tom-bombadil (EDHREC)/
    ├── tom-bombadil.csv          # Full decklist
    ├── owned_cards.csv           # Cards I own (Quantity, Name)
    └── not_owned_cards.csv       # Cards I'm missing (Quantity, Name)
```

Custom decks from CLI use `(Custom)` suffix instead of `(EDHREC)`.

### EDHREC scraping — how it works

EDHREC moved to Next.js. Old CSS scraping broke. Current method (both web + CLI):

1. URL: `https://edhrec.com/average-decks/{slug}`
2. Slugify commander name: remove `,` and `'`, spaces → `-`, lowercase
   - `"K'rrik, Son of Yawgmoth"` → `krrik-son-of-yawgmoth`
3. Parse `<script id="__NEXT_DATA__">` JSON blob
4. Navigate: `props.pageProps.data.deck` → list of `"1 Card Name"` strings
5. Split on first space for quantity + name

Web implementation: `web/routes/commander.py`
CLI implementation: `cli/deckmaster.py` (uses `lxml` parser, web uses `html.parser`)

After scrape, web redirects to deck view. CLI logs file paths.

### Custom decklists (CLI only for now)

Put `.txt` files in `costume DeckLists/` (yes, typo — kept for backwards compat).

Format: first line is commander name, rest is `quantity name` per line.

Override folder:
```bash
export DECKMASTER_CUSTOM_DECKLISTS="custom_decklists"
```

---

## Web app — routes & features

**Stack:** Flask 3 + Jinja2 + vanilla JS. Served via Gunicorn in Docker, Flask dev server locally.

### Routes

| URL | What it does |
|-----|----------------|
| `/` | Lists all folders in `commanders/` |
| `/deck/<folder>` | Deck page — owned/missing cards with Scryfall images |
| `/scrape` | Form to scrape a commander from EDHREC |
| `/api/card-image?id=...` or `?name=...` | Proxy to Scryfall for card images (110ms delay between loads) |

### Deck page features (added Jul 2026)

- Progress bar (owned %)
- Card grid with lazy-loaded Scryfall images
- **Copy / Download .txt** for full decklist and missing cards only
- Plain text format: `1 Sol Ring` per line — works in Moxfield, Manabox, Cardmarket

### Running locally

```bash
pip install -r requirements.txt
python migrate_csv_to_db.py --yes    # if collection.csv at repo root
python app.py                         # debug server on :5000
# or
gunicorn --bind 0.0.0.0:5000 app:app
```

### Running with Docker (preferred for fresh clones)

```bash
# 1. Put ManaBox export at data/collection.csv
# 2. Start
docker compose up --build
# 3. Open http://localhost:5000
```

`docker-entrypoint.sh` auto-migrates CSV → DB on first run if DB doesn't exist yet.

Optional CLI inside Docker:
```bash
docker compose run --rm web python deckmaster.py --commander "Tom Bombadil"
```

---

## DeckMaster CLI

```bash
# Interactive menu
python deckmaster.py

# Scrape EDHREC
python deckmaster.py --commander "Ink-Eyes, Servant of Oni"

# Custom decklist
python deckmaster.py --custom "costume DeckLists/my-deck.txt"
```

### CLI env vars

| Variable | Default |
|----------|---------|
| `DECKMASTER_CUSTOM_DECKLISTS` | `costume DeckLists` |
| `DECKMASTER_COMMANDERS_DIR` | `commanders` |
| `DECKMASTER_COLLECTION_CSV` | `collection.csv` |

Menu options:
1. Scrape from EDHREC
2. Pick a custom decklist from folder
3. Exit

---

## Meta Master — kept but broken

All code lives in `meta/`. Entry point: `python meta_master.py`

### History / why it doesn't work

- Originally scraped **MTGGoldfish** for meta decklists
- MTGGoldfish started blocking automated requests
- Rewrote scraper for **MTGTop8** (`meta/meta_scraper.py`)
- Still flaky / not maintained — I'm OK leaving it broken
- UI text in `meta_master.py` still says "MTGGoldfish" in places (outdated)

### What it was supposed to do

1. Pick format: Pauper, Modern, Vintage, Legacy, Standard
2. Load cached meta data from `meta_cache/{format}_{date}.json` or scrape fresh
3. For each meta deck, calculate collection completion % (quantity-aware)
4. Show top decks ranked by how close I am to building them
5. Optionally export to `meta_decks/{format}/{deck-name}/` with 3 CSVs:
   - `{deck-name}.csv` — full list
   - `owned_cards.csv` — with quantity needed vs owned
   - `not_owned_cards.csv` — missing cards

### Meta file reference

| File | Role |
|------|------|
| `meta/meta_master.py` | Menu loop, orchestrates cache/scrape/analyze |
| `meta/meta_scraper.py` | MTGTop8 HTML scraping, 2s delay between requests |
| `meta/meta_cache.py` | JSON cache in `meta_cache/`, dated filenames |
| `meta/meta_analyzer.py` | Completion math, display, CSV export |

### If I ever fix it

- Update UI strings (MTGGoldfish → MTGTop8)
- Test MTGTop8 HTML structure hasn't changed
- Wire `COLLECTION_DB` env var through meta analyzer (currently hardcoded `collection.db`)
- Consider deleting or archiving if I don't care about constructed formats

---

## Docker reference

### Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.12-slim, installs deps, Gunicorn CMD |
| `docker-compose.yml` | Single `web` service, port 5000, `./data` volume |
| `docker-entrypoint.sh` | Auto-migrate on first run, then exec Gunicorn |
| `.dockerignore` | Excludes `data/`, `commanders/`, caches, `__pycache__` |
| `.gitattributes` | Forces LF line endings on entrypoint (Windows fix) |

### Gunicorn settings

```
--bind 0.0.0.0:5000
--workers 2
--timeout 120    # headroom for Scryfall image fetches
```

### Common Docker commands

```bash
docker compose up --build          # build + start
docker compose up -d               # detached
docker compose down                # stop
docker compose logs -f             # tail logs
docker compose run --rm web python migrate_csv_to_db.py --yes
docker compose run --rm web python deckmaster.py --commander "Sol Ring"
```

---

## Dependencies

```
beautifulsoup4==4.12.3   # HTML parsing (EDHREC, MTGTop8)
requests==2.32.3         # HTTP
Flask==3.0.3             # Web framework
gunicorn==22.0.0         # Production WSGI (Docker only)
```

Built-in: `sqlite3`, `csv`, `json`, `argparse`, `logging`

CLI also uses `lxml` parser in BeautifulSoup but it's not in requirements.txt —
falls back to `html.parser` if lxml not installed (web already uses html.parser).

---

## Gitignored / generated data

| Path | What lives here |
|------|-----------------|
| `commanders/` | Scraped commander deck folders (local dev) |
| `data/*` | Docker persistent data (csv, db, commanders) — `.gitkeep` kept |
| `costume DeckLists/` | Custom deck .txt files |
| `meta_cache/` | Meta JSON caches |
| `meta_decks/` | Exported meta deck CSVs |
| `__pycache__/` | Python bytecode |

`collection.csv` and `collection.db` at repo root are NOT gitignored (my personal data may be tracked).

---

## Known quirks & tech debt

Things I know about but haven't fixed:

1. **CLI EDHREC scrape still reads `collection.csv`** for owned/missing split, while web uses `collection.db`. Should unify on DB.
2. **Web ownership check is binary** (own it or not) — doesn't account for needing 2 copies but only owning 1. Meta analyzer does this correctly.
3. **`costume DeckLists` typo** — folder name has a typo ("costume" not "custom"). Env var `DECKMASTER_CUSTOM_DECKLISTS` lets me override.
4. **`app.py` was duplicated** during reorg — fixed to be wrapper-only.
5. **Meta Master UI mentions MTGGoldfish** but scraper targets MTGTop8.
6. **`db_collection.py` wrapper at root** — `meta_analyzer.py` imports `db_collection` which resolves to root wrapper. Works but slightly confusing.
7. **Scryfall rate limiting** — deck page loads images sequentially with 110ms delay client-side + 100ms server-side. Slow for 100-card decks but avoids 429s.
8. **No tests** — `test.py` exists but isn't a real test suite.
9. **Two parallel data locations** — `data/` for Docker, repo root for local. Pick one workflow and stick to it.

---

## Command cheat sheet

```bash
# ── Setup ──
pip install -r requirements.txt
cp my-export.csv data/collection.csv      # or collection.csv at root for local
python migrate_csv_to_db.py --yes

# ── Web (local) ──
python app.py
gunicorn --bind 0.0.0.0:5000 app:app

# ── Web (Docker) ──
docker compose up --build

# ── CLI ──
python deckmaster.py
python deckmaster.py --commander "Tom Bombadil"
python deckmaster.py --custom "costume DeckLists/deck.txt"

# ── Meta (broken) ──
python meta_master.py

# ── Re-import collection ──
python migrate_csv_to_db.py --yes
docker compose run --rm web python migrate_csv_to_db.py --yes
```

---

## Timeline / evolution notes

- Started as CLI-only EDHREC scraper comparing against CSV collection
- Added SQLite migration from ManaBox CSV (Scryfall IDs for future web use)
- Built Flask web app with card images via Scryfall API
- EDHREC broke (CSS scraping) → switched to `__NEXT_DATA__` JSON parsing
- Added Meta Master for constructed formats (Pauper etc.) — MTGGoldfish blocked us
- Rewrote meta scraper for MTGTop8 — still not really working, parked it
- Added Docker setup so fresh clones are easy to run
- Reorganized repo into `web/`, `cli/`, `meta/`, `collection_tools/` with root wrappers
- Fixed web scrape to output 3 CSV files again (full, owned, not owned)
- Added copy/download decklist buttons on deck page (Moxfield/Manabox/Cardmarket format)

---

## Ideas for later (if I come back to this)

- [ ] Unify CLI on `collection.db` instead of CSV for comparisons
- [ ] Quantity-aware ownership in web app (like meta analyzer)
- [ ] Web UI for custom decklist upload (not just CLI)
- [ ] Fix or delete Meta Master
- [ ] Rename `costume DeckLists` → `custom_decklists` with migration helper
- [ ] Consolidate data paths (always use `data/` even locally)
- [ ] Basic tests for EDHREC JSON parsing and decklist text formatting
- [ ] `Makefile` with `make run`, `make migrate`, `make docker`
