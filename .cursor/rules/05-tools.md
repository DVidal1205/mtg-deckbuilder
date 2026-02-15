# Tool Usage

**Always use `python3` instead of `python` when running Python scripts.** The system uses Python 3, and `python` may not be available or may point to Python 2.

All card data tools use the **local SQLite database** at `data/cards.db`. Do NOT make external API calls to Scryfall. Only EDHREC tools make external HTTP requests.

**The local database is the source of truth for card legality.** Never suggest the DB is wrong or that a card marked banned might be legal elsewhere. If the DB says a card is banned, treat it as banned.

## Card Search (`tools/card_search.py`)

Search for cards using flexible filters.

```bash
python3 tools/card_search.py --color-identity "WUB" --type "creature" --cmc-max 3 --text "draw" --commander-legal --max 20
```

### Available Flags
- `--name "partial name"` — Name contains (case-insensitive)
- `--color-identity "WUB"` — Within this color identity (for Commander)
- `--colors "UB"` — Exact colors
- `--type "creature"` — Type line contains
- `--text "oracle text"` — Oracle text contains (case-insensitive)
- `--cmc-min N` / `--cmc-max N` — Mana value range
- `--power-min N` / `--power-max N` — Power range (creatures)
- `--toughness-min N` / `--toughness-max N` — Toughness range
- `--keyword "flying"` — Has keyword
- `--rarity "mythic"` — Rarity filter
- `--commander-legal` — Only Commander-legal cards
- `--game-changer` — Only cards on the DB game-changers list (B3: max 3 per deck)
- `--no-game-changer` — Exclude game changers
- `--is-commander` — Only legendary creatures (potential commanders)
- `--max N` — Max results (default 20)
- `--sort "edhrec_rank"` — Sort by field (edhrec_rank, cmc, name, power)
- `--tag "blink"` — Has mechanic tag (supports multiple, OR'd)
- `--fts "NEAR(sacrifice creature)"` — FTS5 full-text search (supports AND, OR, NEAR(), NOT, `"phrases"`)
- `--like "Grave Pact"` — Find cards similar to a known card (by keywords, types, mechanic tags)
- `--sql "raw WHERE clause"` — Escape hatch for complex queries

**FTS5 syntax tips**: Use `"phrase match"` for exact phrases, `term1 AND term2` for both terms, `term1 OR term2` for either, `NEAR(term1 term2)` for proximity, `NOT term` to exclude.

Output concise card summaries, not raw JSON/SQL.

## Card Lookup (`tools/card_lookup.py`)

Get full details for a specific card.

```bash
python3 tools/card_lookup.py "Rhystic Study"
```

- Exact match first, then fuzzy/partial match fallback
- Show: name, mana cost, type, full oracle text, power/toughness, color identity, mechanic tags, **game changer** (if on DB list), format legality, EDHREC rank
- If multiple matches (e.g., DFCs), show all faces

## Color Identity Search (`tools/color_identity.py`)

Quick utility: find all commanders or all cards within a color identity.

```bash
python3 tools/color_identity.py "GU" --commanders-only --sort edhrec_rank --max 30
```

Useful for: "show me all Simic commanders" or "what Boros cards have 'exile' in their text?"

## EDHREC Commander Data (`tools/edhrec_commander.py`)

Fetch data from EDHREC for a specific commander. Uses the `pyedhrec` library (installed in `.venv`).

```bash
python3 tools/edhrec_commander.py "Meren of Clan Nel Toth"
python3 tools/edhrec_commander.py "Meren of Clan Nel Toth" --section high-synergy
python3 tools/edhrec_commander.py "Meren of Clan Nel Toth" --section creatures
```

### Available Sections
- `overview` (default) — Deck count, top cards, and general commander stats
- `high-synergy` — Cards with highest synergy scores for this commander
- `new` — Recently printed cards seeing play
- `top` — Most-played cards overall
- `creatures`, `instants`, `sorceries`, `enchantments`, `artifacts`, `mana-artifacts`, `planeswalkers`, `lands`, `utility-lands` — Top cards by type
- `combos` — Known combo lines
- `average-deck` — EDHREC's average decklist
- `decks` — Sample decklists

Uses `pyedhrec.EDHRec` methods: `get_commander_data()`, `get_commander_cards()`, `get_high_synergy_cards()`, `get_top_cards()`, `get_commanders_average_deck()`, `get_commander_decks()`, `get_card_combos()`, etc.

Handle network errors and missing commanders gracefully.

### EDHREC usage principle

**Use EDHREC to guide, not as a single source of truth.** EDHREC stats aggregate all decks that run a given commander; those decks can have drastically different game plans (combo, tribal, control, storm, etc.). The **source of truth** for any deck is the **owner’s playstyle and game plan** as stated in that deck’s file (strategy, win conditions, bracket, and notes). When suggesting adds or cuts, prioritize fit with the deck file’s stated plan; use EDHREC to discover options, fill gaps, or validate direction, not to override the deck’s intended identity.

## EDHREC Top Cards (`tools/edhrec_top_cards.py`)

Get top/staple cards for a commander, broken down by type. Uses `pyedhrec`.

```bash
python3 tools/edhrec_top_cards.py "Korvold, Fae-Cursed King"
python3 tools/edhrec_top_cards.py "Korvold, Fae-Cursed King" --type creatures --max 15
```

- Query EDHREC for staples associated with a commander
- Filter by card type (creatures, instants, sorceries, enchantments, artifacts, lands, etc.)
- Useful for finding cards you might miss or checking what the community runs

## Deck Stats (`tools/deck_stats.py`)

Analyze a saved decklist.

```bash
python3 tools/deck_stats.py decks/meren-reanimator.md
```

Output:
```
=== Deck Stats: Meren Reanimator ===
Commander: Meren of Clan Nel Toth
Color Identity: BG

Card Count: 100 (✓)
Lands: 37 | Nonlands: 62 + Commander

Mana Curve (nonland, non-free):
  0: ██ 3
  1: ████████ 8
  2: ████████████████ 16
  3: ██████████████ 14
  4: ██████████ 10
  5: ██████ 6
  6: ████ 4
  7+: ██ 2
Average MV: 2.85

Mana sources (lands + rocks / Add mana):
  Blue    : 26 sources  (55.3%)
  Red     : 21 sources  (44.7%)

Card Types:
  Creatures: 32
  Instants: 8
  Sorceries: 10
  Enchantments: 5
  Artifacts: 5
  Planeswalkers: 2
  Lands: 37
  
Category Estimates (heuristic):
  Ramp: ~12
  Card Draw: ~10
  Removal: ~8
  Board Wipes: ~3

Singleton Check: ✓ No duplicates (excluding basics)
Color Identity Check: ✓ All cards within BG
Commander Legality: ✓ All cards legal in Commander
```

**Mana sources:** Counts lands and nonlands that produce mana (oracle "Add {U}", "Add one mana of any color", fetches that find Island/Mountain, etc.). Each dual counts as 1 source per color it produces. Only colors in the deck's color identity are shown. Use to balance the manabase; see `.cursor/rules/07-mana-base.md`.

The category estimates should be heuristic — scan oracle text for keywords like "search your library for a land" (ramp), "draw" (card draw), "destroy" / "exile" (removal), "each" + "destroy"/"exile"/"damage" (wipe), etc. It won't be perfect but gives a quick sanity check.

## Fetch Full Deck (`tools/fetch_full_deck.py`)

Export every card in a decklist with **mana cost and oracle text** for LLM context. Use this when the user asks for deck changes, adds, cuts, or swaps so you have full card text without re-querying the DB for each card.

```bash
python3 tools/fetch_full_deck.py decks/mizzix-of-the-izmagnus.md
```

- Parses the deck file (same format as deck_stats: `.md` with fenced code block, or `.txt` with `N Card Name` lines)
- Looks up each unique card in the local DB for `mana_cost` and `oracle_text` (and `face_oracle_texts` for split/DFC)
- Outputs one block: `Nx Card Name (mana_cost): oracle text...` per unique card, in deck order
- **When to use:** Before proposing specific swaps, cuts, or adds for an existing deck, run `fetch_full_deck` on that deck file and use the output as context so your suggestions are accurate (you see exact costs and rules text)

## Validate Type Counts (`tools/validate_types.py`)

Validate (and optionally fix) the type count tables in deck `.md` files. Uses the local DB for card type lookups, with Scryfall API fallback for cards not in the DB (e.g., Universes Beyond / crossover cards).

```bash
python3 tools/validate_types.py decks/im-tophin-it.md          # single deck
python3 tools/validate_types.py decks/the-gob.md decks/mr-freaky.md  # multiple decks
python3 tools/validate_types.py --all                            # all decks
python3 tools/validate_types.py --all --fix                      # validate + auto-fix tables
```

### Flags
- `decks ...` — One or more deck `.md` file paths
- `--all` — Validate every `.md` file in `decks/`
- `--fix` — Auto-replace type count tables in-place with correct values

### What it checks
- Parses the decklist from the fenced code block
- Looks up each card's type (local DB first, Scryfall fallback)
- Compares actual type counts against the listed table
- Reports mismatches with ✅/❌
- Verifies total card count = 100

### Type classification
- For MDFCs (double-faced cards), the **front face** determines the type
- Priority: Creature > Planeswalker > Land > Instant > Sorcery > Enchantment > Artifact
- Artifact Creatures and Enchantment Creatures count as **Creature**

**Run this after any decklist change** to keep type tables accurate.

## Tool Design Principles

- All tools are standalone Python scripts callable from the command line
- Use only standard library + `pyedhrec` (for EDHREC data) + `requests` (for external calls) + `sqlite3` (for local DB). No heavy frameworks
- Output should be **concise, human-readable text** — not raw JSON or SQL results
- Handle errors gracefully — missing cards, network failures, malformed input
- Include `--help` for every tool
