#!/usr/bin/env python3
"""
card_lookup.py — Look up full details for a specific card from the local SQLite database.

Exact match first, then fuzzy/partial fallback. Shows all card details relevant
to Commander deckbuilding.

Usage:
    python tools/card_lookup.py "Rhystic Study"
    python tools/card_lookup.py "rhystic"          # partial match fallback
    python tools/card_lookup.py "Delver of Secr"   # partial match fallback
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import textwrap
from typing import List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cards.db")

# Columns to display
DISPLAY_COLS = [
    "name", "mana_cost", "cmc", "type_line", "oracle_text",
    "face_names", "face_mana_costs", "face_type_lines", "face_oracle_texts",
    "power", "toughness", "loyalty", "defense",
    "colors", "color_identity", "keywords", "mechanic_tags",
    "rarity", "set_name", "edhrec_rank",
    "legal_commander", "legal_vintage", "legal_legacy", "legal_modern",
    "scryfall_uri", "image_normal",
]


def lookup_card(conn: sqlite3.Connection, name: str) -> List[dict]:
    """Try exact match, then LIKE match, return list of matching cards."""
    conn.row_factory = sqlite3.Row

    # 1. Exact match (case-insensitive)
    row = conn.execute(
        "SELECT * FROM cards WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return [dict(row)]

    # 2. Partial match — name starts with input
    rows = conn.execute(
        "SELECT * FROM cards WHERE name LIKE ? COLLATE NOCASE ORDER BY edhrec_rank IS NULL, edhrec_rank ASC LIMIT 10",
        (f"{name}%",)
    ).fetchall()
    if rows:
        return [dict(r) for r in rows]

    # 3. Broader partial match — name contains input
    rows = conn.execute(
        "SELECT * FROM cards WHERE name LIKE ? COLLATE NOCASE ORDER BY edhrec_rank IS NULL, edhrec_rank ASC LIMIT 10",
        (f"%{name}%",)
    ).fetchall()
    if rows:
        return [dict(r) for r in rows]

    # 4. FTS5 fuzzy search as last resort
    try:
        rows = conn.execute(
            """SELECT c.* FROM cards c
               JOIN cards_fts ON cards_fts.rowid = c.rowid
               WHERE cards_fts MATCH ?
               ORDER BY c.edhrec_rank IS NULL, c.edhrec_rank ASC
               LIMIT 10""",
            (name,)
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        pass  # FTS query might fail on special characters

    return []


def format_full_card(card: dict) -> str:
    """Format a card with full details for display."""
    lines = []
    name = card.get("name", "Unknown")
    mana = card.get("mana_cost") or ""
    sep = "═" * max(60, len(name) + len(mana) + 5)

    lines.append(sep)
    lines.append(f"  {name}  {mana}")
    lines.append(sep)

    # Type line
    type_line = card.get("type_line") or ""
    lines.append(f"  Type:           {type_line}")

    # P/T, Loyalty, Defense
    if card.get("power") is not None and card.get("toughness") is not None:
        lines.append(f"  Power/Tough:    {card['power']}/{card['toughness']}")
    if card.get("loyalty"):
        lines.append(f"  Loyalty:        {card['loyalty']}")
    if card.get("defense"):
        lines.append(f"  Defense:        {card['defense']}")

    # CMC
    cmc = card.get("cmc")
    if cmc is not None:
        lines.append(f"  Mana Value:     {cmc}")

    # Colors and color identity
    colors = card.get("colors") or "Colorless"
    ci = card.get("color_identity") or "Colorless"
    lines.append(f"  Colors:         {colors}")
    lines.append(f"  Color Identity: {ci}")

    lines.append("")

    # Oracle text
    oracle = card.get("oracle_text") or ""
    if oracle:
        lines.append("  Oracle Text:")
        for para in oracle.split("\n"):
            wrapped = textwrap.fill(para, width=72, initial_indent="    ", subsequent_indent="    ")
            lines.append(wrapped)
        lines.append("")

    # DFC / Multi-face
    face_names = card.get("face_names") or ""
    if face_names and "," in face_names:
        lines.append("  ── Card Faces ──")
        f_names = (face_names or "").split(",")
        f_costs = (card.get("face_mana_costs") or "").split(",")
        f_types = (card.get("face_type_lines") or "").split(",")
        f_texts = (card.get("face_oracle_texts") or "").split(";;")  # might vary

        for i, fn in enumerate(f_names):
            fn = fn.strip()
            fc = f_costs[i].strip() if i < len(f_costs) else ""
            ft = f_types[i].strip() if i < len(f_types) else ""
            lines.append(f"  Face {i+1}: {fn}  {fc}")
            lines.append(f"    Type: {ft}")
            if i < len(f_texts):
                ftxt = f_texts[i].strip()
                if ftxt:
                    for para in ftxt.split("\n"):
                        wrapped = textwrap.fill(para, width=68, initial_indent="      ", subsequent_indent="      ")
                        lines.append(wrapped)
            lines.append("")

    # Keywords
    kws = card.get("keywords") or ""
    if kws:
        lines.append(f"  Keywords:       {kws}")

    # Mechanic tags
    tags = card.get("mechanic_tags") or ""
    if tags:
        lines.append(f"  Mechanic Tags:  {tags}")

    # Game changer (DB list; B3 decks typically max 3)
    if card.get("game_changer") == 1:
        lines.append("  Game Changer:   Yes")

    # Set info
    set_name = card.get("set_name") or ""
    rarity = card.get("rarity") or ""
    lines.append(f"  Set:            {set_name} ({rarity})")

    # EDHREC rank
    rank = card.get("edhrec_rank")
    if rank:
        lines.append(f"  EDHREC Rank:    #{rank}")

    # Legality
    lines.append("")
    lines.append("  Format Legality:")
    for fmt in ["commander", "vintage", "legacy", "modern"]:
        col = f"legal_{fmt}"
        val = card.get(col) or "unknown"
        status = "✓ Legal" if val == "legal" else "✗ " + val.replace("_", " ").title()
        lines.append(f"    {fmt.title():12s} {status}")

    # Links
    scryfall = card.get("scryfall_uri") or ""
    if scryfall:
        lines.append("")
        lines.append(f"  Scryfall:       {scryfall}")

    lines.append(sep)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Look up full details for a specific MTG card.",
    )
    parser.add_argument("card_name", nargs="+", help="Card name (exact or partial)")
    parser.add_argument("--db", type=str, default=DB_PATH, help=argparse.SUPPRESS)

    args = parser.parse_args()
    card_name = " ".join(args.card_name)

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    results = lookup_card(conn, card_name)
    conn.close()

    if not results:
        print(f"No cards found matching '{card_name}'.")
        sys.exit(1)

    if len(results) == 1:
        print(format_full_card(results[0]))
    else:
        # Multiple matches — show the first one fully, list the rest
        print(format_full_card(results[0]))
        if len(results) > 1:
            print(f"\n  Also matched ({len(results) - 1} more):")
            for r in results[1:]:
                mana = r.get("mana_cost") or ""
                tl = r.get("type_line") or ""
                print(f"    • {r['name']}  {mana}  — {tl}")


if __name__ == "__main__":
    main()
