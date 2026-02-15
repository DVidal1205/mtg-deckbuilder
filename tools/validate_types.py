#!/usr/bin/env python3
"""
validate_types.py — Validate and fix type count tables in deck markdown files.

Parses the decklist from each .md file, looks up card types (local DB first,
Scryfall API fallback for cards not found), and compares against the listed
type count table. Reports mismatches and optionally fixes them in-place.

Usage:
    python3 tools/validate_types.py decks/im-tophin-it.md
    python3 tools/validate_types.py --all
    python3 tools/validate_types.py decks/the-gob.md --fix
    python3 tools/validate_types.py --all --fix
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / ".." / "data" / "cards.db"
DECKS_DIR = SCRIPT_DIR / ".." / "decks"

BASIC_LANDS = {"mountain", "plains", "forest", "island", "swamp", "wastes"}

TYPE_ORDER = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact",
              "Planeswalker", "Land", "Battle"]


# ── Decklist parsing ─────────────────────────────────────────────────────────

def parse_decklist(filepath: Path) -> List[Tuple[int, str]]:
    """Extract (quantity, card_name) pairs from the fenced code block."""
    content = filepath.read_text(encoding="utf-8")
    match = re.search(r"```\n(.*?)```", content, re.DOTALL)
    if not match:
        return []
    cards: List[Tuple[int, str]] = []
    for line in match.group(1).strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\s+(.+)$", line)
        if m:
            cards.append((int(m.group(1)), m.group(2).strip()))
    return cards


def parse_listed_counts(filepath: Path) -> Dict[str, int]:
    """Extract the type → count mapping from the markdown table."""
    content = filepath.read_text(encoding="utf-8")
    listed: Dict[str, int] = {}
    table_match = re.search(
        r"\| Type \| Count \|.*?\n\|[-\s|]+\n((?:\|.*\|.*\n)+)", content
    )
    if table_match:
        for row in table_match.group(1).strip().split("\n"):
            m = re.match(r"\|\s*(\w+)\s*\|\s*(\d+)\s*\|", row)
            if m:
                listed[m.group(1)] = int(m.group(2))
    return listed


# ── Type classification ──────────────────────────────────────────────────────

def classify_type(type_line: str) -> str:
    """Classify a card by its type line. For MDFCs, uses front face only."""
    tl = type_line.lower()
    if " // " in tl:
        tl = tl.split(" // ")[0].strip()
    if "creature" in tl:
        return "Creature"
    if "planeswalker" in tl:
        return "Planeswalker"
    if "land" in tl:
        return "Land"
    if "instant" in tl:
        return "Instant"
    if "sorcery" in tl:
        return "Sorcery"
    if "enchantment" in tl:
        return "Enchantment"
    if "artifact" in tl:
        return "Artifact"
    if "battle" in tl:
        return "Battle"
    return "Unknown"


# ── Local DB lookup ──────────────────────────────────────────────────────────

def lookup_local(conn: sqlite3.Connection, names: List[str]) -> Dict[str, str]:
    """Look up type_line for each card in the local SQLite DB.

    Returns {card_name: type_line} for cards found.
    """
    conn.row_factory = sqlite3.Row
    result: Dict[str, str] = {}
    for name in names:
        # Exact match
        row = conn.execute(
            "SELECT type_line FROM cards WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            result[name] = row["type_line"]
            continue
        # Front-face match for MDFCs
        if " // " in name:
            front = name.split(" // ")[0].strip()
            row = conn.execute(
                "SELECT type_line FROM cards WHERE name LIKE ? COLLATE NOCASE LIMIT 1",
                (f"{front}%",),
            ).fetchone()
            if row:
                result[name] = row["type_line"]
                continue
        # Prefix match fallback
        row = conn.execute(
            "SELECT type_line FROM cards WHERE name LIKE ? COLLATE NOCASE LIMIT 1",
            (f"{name}%",),
        ).fetchone()
        if row:
            result[name] = row["type_line"]
    return result


# ── Scryfall fallback ────────────────────────────────────────────────────────

def lookup_scryfall(names: List[str]) -> Dict[str, str]:
    """Look up type_line for cards via Scryfall /cards/collection endpoint.

    Returns {card_name: type_line} for cards found. Batches in groups of 75.
    """
    if requests is None:
        print("  ⚠ requests library not installed; skipping Scryfall fallback",
              file=sys.stderr)
        return {}

    result: Dict[str, str] = {}
    for i in range(0, len(names), 75):
        batch = names[i : i + 75]
        identifiers = []
        for name in batch:
            search_name = name.split(" // ")[0].strip() if " // " in name else name
            identifiers.append({"name": search_name})

        try:
            resp = requests.post(
                "https://api.scryfall.com/cards/collection",
                json={"identifiers": identifiers},
                timeout=15,
            )
            data = resp.json()
        except Exception as e:
            print(f"  ⚠ Scryfall request failed: {e}", file=sys.stderr)
            continue

        if "data" in data:
            for card in data["data"]:
                full_name = card["name"]
                type_line = card.get("type_line", "")
                result[full_name] = type_line
                # Also map front-face name for MDFC matching
                if " // " in full_name:
                    front = full_name.split(" // ")[0].strip()
                    result[front] = type_line

        if data.get("not_found"):
            for nf in data["not_found"]:
                print(f"  ⚠ Not found on Scryfall: {nf.get('name', nf)}",
                      file=sys.stderr)

        time.sleep(0.15)  # respect Scryfall rate limits

    return result


# ── Type counting ────────────────────────────────────────────────────────────

def count_types(
    cards: List[Tuple[int, str]], type_map: Dict[str, str]
) -> Tuple[Dict[str, int], List[str]]:
    """Count card types using the type_map. Returns (counts, not_found_names)."""
    counts: Dict[str, int] = defaultdict(int)
    not_found: List[str] = []

    for qty, name in cards:
        if name.lower() in BASIC_LANDS:
            counts["Land"] += qty
            continue

        type_line = type_map.get(name)
        # Try front-face lookup for MDFCs
        if type_line is None and " // " in name:
            front = name.split(" // ")[0].strip()
            type_line = type_map.get(front)
        # Try case-insensitive prefix match
        if type_line is None:
            key_lower = name.lower()
            for k, v in type_map.items():
                if k.lower().startswith(key_lower) or key_lower.startswith(k.lower()):
                    type_line = v
                    break

        if type_line:
            card_type = classify_type(type_line)
            counts[card_type] += qty
        else:
            not_found.append(name)

    return dict(counts), not_found


# ── Fix the type table in-place ──────────────────────────────────────────────

def fix_type_table(filepath: Path, actual: Dict[str, int]) -> bool:
    """Replace the type count table in the .md file with correct counts.

    Returns True if the file was modified.
    """
    content = filepath.read_text(encoding="utf-8")

    # Build new table
    lines = ["| Type | Count |", "|------|-------|"]
    for t in TYPE_ORDER:
        c = actual.get(t, 0)
        if c > 0:
            lines.append(f"| {t} | {c} |")
    new_table = "\n".join(lines) + "\n"

    # Find existing table and replace it
    pattern = re.compile(
        r"\| Type \| Count \|\n\|[-\s|]+\n(?:\|.*\|.*\n)+", re.MULTILINE
    )
    match = pattern.search(content)
    if not match:
        return False

    new_content = content[: match.start()] + new_table + content[match.end() :]
    if new_content == content:
        return False

    filepath.write_text(new_content, encoding="utf-8")
    return True


# ── Main ─────────────────────────────────────────────────────────────────────

def validate_deck(
    filepath: Path,
    conn: Optional[sqlite3.Connection],
    scryfall_cache: Dict[str, str],
    fix: bool = False,
) -> bool:
    """Validate a single deck file. Returns True if counts are correct."""
    cards = parse_decklist(filepath)
    if not cards:
        print(f"⚠ {filepath.name}: no decklist found")
        return False

    listed = parse_listed_counts(filepath)
    total_cards = sum(qty for qty, _ in cards)

    # Build type map: local DB first, Scryfall for missing
    unique_names = [name for _, name in cards if name.lower() not in BASIC_LANDS]
    unique_names = list(dict.fromkeys(unique_names))  # dedupe, preserve order

    type_map: Dict[str, str] = {}

    # Local DB lookup
    if conn is not None:
        type_map.update(lookup_local(conn, unique_names))

    # Find names not resolved locally
    missing = [n for n in unique_names if n not in type_map
               and (n.split(" // ")[0].strip() if " // " in n else n) not in type_map]

    # Scryfall fallback for missing cards (check cache first)
    still_missing = []
    for name in missing:
        search = name.split(" // ")[0].strip() if " // " in name else name
        if search in scryfall_cache:
            type_map[name] = scryfall_cache[search]
        elif name in scryfall_cache:
            type_map[name] = scryfall_cache[name]
        else:
            still_missing.append(name)

    if still_missing:
        sf_results = lookup_scryfall(still_missing)
        scryfall_cache.update(sf_results)
        type_map.update(sf_results)

    actual, not_found = count_types(cards, type_map)

    # Compare
    all_match = True
    diffs: List[str] = []
    for t in TYPE_ORDER:
        a = actual.get(t, 0)
        l = listed.get(t, 0)
        if a != l:
            all_match = False
            diffs.append(f"    {t}: listed {l} → actual {a}")

    # Check for types in listed but not in actual
    for t in listed:
        if t not in actual and listed[t] > 0:
            all_match = False
            diffs.append(f"    {t}: listed {listed[t]} → actual 0")

    listed_total = sum(listed.values())

    if all_match and total_cards == 100 and listed_total == 100:
        print(f"✅ {filepath.name} — {total_cards} cards, all type counts correct")
        return True

    print(f"❌ {filepath.name} — {total_cards} cards (table sums to {listed_total})")
    for d in diffs:
        print(d)

    if not_found:
        print(f"    ⚠ {len(not_found)} card(s) not resolved: {not_found[:5]}")

    if fix:
        if fix_type_table(filepath, actual):
            print(f"    → Fixed type table in {filepath.name}")
        else:
            print(f"    → No change needed or table not found")

    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate type count tables in deck .md files."
    )
    parser.add_argument(
        "decks", nargs="*",
        help="Path(s) to deck .md file(s). Omit and use --all for every deck.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Validate all .md files in the decks/ directory.",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Auto-fix type count tables in-place.",
    )
    args = parser.parse_args()

    if not args.decks and not args.all:
        parser.print_help()
        sys.exit(1)

    # Resolve deck files
    if args.all:
        deck_files = sorted(DECKS_DIR.glob("*.md"))
    else:
        deck_files = [Path(p) for p in args.decks]

    if not deck_files:
        print("No deck files found.", file=sys.stderr)
        sys.exit(1)

    # Open local DB if available
    conn: Optional[sqlite3.Connection] = None
    db = DB_PATH.resolve()
    if db.exists():
        conn = sqlite3.connect(str(db))

    scryfall_cache: Dict[str, str] = {}
    passed = 0
    total = len(deck_files)

    for f in deck_files:
        if not f.exists():
            print(f"⚠ File not found: {f}", file=sys.stderr)
            continue
        ok = validate_deck(f, conn, scryfall_cache, fix=args.fix)
        if ok:
            passed += 1

    if conn:
        conn.close()

    print(f"\n{passed}/{total} decks passed validation.")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
