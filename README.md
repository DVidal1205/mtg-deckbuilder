# MTG Commander Deckbuilder

An AI-assisted **Commander/EDH** deckbuilding workspace. This is not a traditional software project — it's a conversational environment where you interact with the AI in Cursor to build, iterate, and refine Commander decks.

Most of the work happens through strategic conversation: discussing commanders, evaluating cards, debating includes, and tuning decklists. The code in this repo is **tooling** that supports that conversation.

## How to Use

1. **Open this project in [Cursor](https://cursor.sh)**
2. **Use Composer or Agent mode** to start a deckbuilding conversation
3. The AI reads the `.cursor/rules/` files automatically and operates as an expert Commander deckbuilder
4. Ask it to build a deck, evaluate cards, suggest cuts, analyze your list, or pull EDHREC data

### Example prompts
- *"Build me a Meren of Clan Nel Toth reanimator deck, bracket 3"*
- *"What are the best sacrifice payoffs in Golgari?"*
- *"Analyze my Korvold list and suggest cuts"*
- *"What does EDHREC say people are running in Atraxa?"*
- *"Find me cards similar to Grave Pact in black-green"*

## Setup

### 1. Clone and enter the project
```bash
git clone <your-repo-url>
cd mtg-deckbuilder
```

### 2. Create a virtual environment and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Download Scryfall bulk data
1. Go to [Scryfall Bulk Data](https://scryfall.com/docs/api/bulk-data)
2. Download the **Oracle Cards** file (the one with unique cards, no reprints)
3. Save it as `data/cards.json`

### 4. Convert to CSV and SQLite
Use the included conversion utility:
```bash
# If you need a CSV (optional — the JSON can be converted directly)
python utils/convert.py  # or your preferred conversion method

# Build the SQLite database from the CSV
python utils/csv_to_sqlite.py data/cards.csv data/cards.db
```

The SQLite database at `data/cards.db` is the primary data source for all tools.

### 5. Verify the setup
```bash
# Search for a card
python tools/card_lookup.py "Sol Ring"

# Search for Simic commanders
python tools/color_identity.py GU --commanders-only --max 10

# Test card search with discovery
python tools/card_search.py --text "when a creature dies" --color-identity BG --commander-legal --max 10
```

## Project Structure

```
mtg-deckbuilder/
├── .cursor/rules/           # AI behavior rules (read automatically by Cursor)
│   ├── 00-role.md           # Role, identity, and behavioral rules
│   ├── 01-process.md        # Staged deckbuilding process
│   ├── 02-deckbuilding-heuristics.md  # Card counts, mana base, core numbers
│   ├── 03-commander-rules.md          # Commander format rules reference
│   ├── 04-brackets.md       # Bracket/power level system
│   ├── 05-tools.md          # Tool usage documentation
│   └── 06-output-format.md  # Decklist and notes output formats
├── tools/                   # CLI tools for card search, EDHREC, and analysis
│   ├── card_search.py       # Flexible card search with discovery features
│   ├── card_lookup.py       # Exact card lookup with full details
│   ├── color_identity.py    # Browse cards/commanders by color identity
│   ├── edhrec_commander.py  # Fetch EDHREC commander data (uses pyedhrec)
│   ├── edhrec_top_cards.py  # Get top cards for a commander from EDHREC
│   ├── deck_stats.py        # Analyze a decklist (curve, pips, categories)
├── utils/                   # Data conversion and setup utilities
│   ├── csv_to_sqlite.py     # Build SQLite DB from Scryfall CSV
│   └── ...
├── data/                    # Card data (gitignored — large files)
│   ├── cards.json           # Scryfall oracle-cards bulk export
│   ├── cards.csv            # Flattened CSV version
│   └── cards.db             # SQLite database (primary data source)
├── decks/                   # Saved decklists (.md files, import-ready)
├── notes/                   # Playtest notes and session logs
├── requirements.txt
└── README.md
```

## Tools Reference

All tools are standalone Python scripts with `--help`. They use the local SQLite database for card data and `pyedhrec` for EDHREC queries.

### card_search.py — Card Search & Discovery
```bash
# Structured search
python tools/card_search.py --type creature --cmc-max 3 --color-identity WU --commander-legal

# Multi-pattern oracle text (OR'd together)
python tools/card_search.py --text "sacrifice a creature" "when a creature dies" --color-identity BG

# FTS5 full-text search
python tools/card_search.py --fts "exile NEAR graveyard" --commander-legal

# Find cards similar to a known card
python tools/card_search.py --like "Grave Pact" --color-identity BG --commander-legal

# Potential commanders
python tools/card_search.py --is-commander --color-identity GU --max 20
```

### card_lookup.py — Card Details
```bash
python tools/card_lookup.py "Rhystic Study"
python tools/card_lookup.py "rhystic"    # fuzzy match
```

### color_identity.py — Browse by Color Identity
```bash
python tools/color_identity.py GU --commanders-only --max 30
python tools/color_identity.py RW --text exile --commander-legal
python tools/color_identity.py C --commanders-only   # colorless commanders
```

### edhrec_commander.py — EDHREC Commander Data
```bash
python tools/edhrec_commander.py "Meren of Clan Nel Toth"
python tools/edhrec_commander.py "Meren of Clan Nel Toth" --section high-synergy
python tools/edhrec_commander.py "Meren of Clan Nel Toth" --section combos
python tools/edhrec_commander.py "Meren of Clan Nel Toth" --section average-deck
```

### edhrec_top_cards.py — EDHREC Top Cards
```bash
python tools/edhrec_top_cards.py "Korvold, Fae-Cursed King"
python tools/edhrec_top_cards.py "Korvold, Fae-Cursed King" --type creatures --max 15
```

### deck_stats.py — Deck Analysis
```bash
python tools/deck_stats.py decks/meren-of-clan-nel-toth.md
```

## Design Principles

- **Commander/EDH only.** No other formats.
- **Budget is never a concern.** Proxies and online play mean every card is on the table. No price filtering, no budget suggestions, no price data shown.
- **Local-first card data.** All card lookups hit the local SQLite database. Only EDHREC queries go external.
- **Conversation over code.** The AI's primary output is strategic advice and decklists, not code.
- **The AI verifies with tools.** Card details, legality, and color identity are always checked against the database — never from memory alone.
