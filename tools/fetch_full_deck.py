#!/usr/bin/env python3
"""
fetch_full_deck.py — Export every card in a decklist with mana cost, keywords, and oracle text.

Parses a deck .md (or .txt) file, looks up each card in the local database, and
outputs a single block of text suitable for pasting into an LLM context. Use this
when you want to discuss changes, adds, or cuts so the model has full card text
without re-querying. Keywords (e.g. flying, reach) are included because they often
do not appear in oracle text.

Usage:
    python tools/fetch_full_deck.py decks/mizzix-of-the-izmagnus.md
    python tools/fetch_full_deck.py decks/meren.md --db data/cards.db

Output format (one line per unique card):
    Nx Card Name (mana_cost) [Keywords: flying, reach]: oracle text here...
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import OrderedDict
from typing import Dict, List, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cards.db")


def parse_decklist(filepath: str) -> List[Tuple[int, str]]:
    """Parse decklist file. Returns [(count, card_name), ...] in deck order."""
    cards: List[Tuple[int, str]] = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if filepath.lower().endswith(".md"):
        fence_pattern = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
        for fence_match in fence_pattern.finditer(content):
            block = fence_match.group(1)
            for line in block.strip().split("\n"):
                line = line.strip()
                m = re.match(r"^(\d+)\s+(.+)$", line)
                if m:
                    count = int(m.group(1))
                    name = m.group(2).strip()
                    cards.append((count, name))
            break  # use first code block only
    else:
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            m = re.match(r"^(\d+)\s+(.+)$", line)
            if m:
                cards.append((int(m.group(1)), m.group(2).strip()))

    return cards


def aggregate_counts(cards: List[Tuple[int, str]]) -> OrderedDict[str, int]:
    """Return ordered dict of card_name -> total count (preserving first-appearance order)."""
    seen: OrderedDict[str, int] = OrderedDict()
    for count, name in cards:
        seen[name] = seen.get(name, 0) + count
    return seen


def lookup_cards(conn: sqlite3.Connection, names: List[str]) -> Dict[str, dict]:
    """Look up name, mana_cost, oracle_text, face_oracle_texts, keywords for each name."""
    conn.row_factory = sqlite3.Row
    result = {}
    cols = "name, mana_cost, oracle_text, face_oracle_texts, keywords"
    for name in names:
        row = conn.execute(
            f"SELECT {cols} FROM cards WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        if row:
            result[name] = dict(row)
        else:
            row = conn.execute(
                f"SELECT {cols} FROM cards WHERE name LIKE ? COLLATE NOCASE LIMIT 1",
                (f"{name}%",),
            ).fetchone()
            if row:
                result[name] = dict(row)
    return result


def format_oracle(card: dict) -> str:
    """Single string: oracle_text, and if present face_oracle_texts (e.g. ' // ' joined)."""
    main = (card.get("oracle_text") or "").strip()
    face = (card.get("face_oracle_texts") or "").strip()
    if face:
        # face_oracle_texts may use ;; or similar between faces
        parts = [p.strip() for p in face.replace(";;", " // ").split(" // ") if p.strip()]
        if parts:
            return main + " // " + " // ".join(parts) if main else " // ".join(parts)
    return main or "(no oracle text)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export decklist with mana cost and oracle text for LLM context."
    )
    parser.add_argument("decklist", help="Path to decklist file (.md or .txt)")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Path to cards.db")
    args = parser.parse_args()

    if not os.path.exists(args.decklist):
        print(f"Error: File not found: {args.decklist}", file=sys.stderr)
        return 1
    if not os.path.exists(args.db):
        print(f"Error: Database not found: {args.db}", file=sys.stderr)
        return 1

    cards = parse_decklist(args.decklist)
    if not cards:
        print("Error: No card lines found in decklist.", file=sys.stderr)
        return 1

    name_to_count = aggregate_counts(cards)
    conn = sqlite3.connect(args.db)
    data = lookup_cards(conn, list(name_to_count.keys()))
    conn.close()

    print("FULL DECK (cost + keywords + oracle text for LLM context)")
    print("---")
    for name, count in name_to_count.items():
        card = data.get(name, {})
        cost = (card.get("mana_cost") or "—").strip()
        keywords = (card.get("keywords") or "").strip()
        oracle = format_oracle(card)
        if not card:
            oracle = "(not in database)"
        # Include keywords so flying/reach/etc. are visible even when not in oracle text
        kw_part = f" [Keywords: {keywords}]" if keywords else ""
        line = f"{count}x {name} ({cost}){kw_part}: {oracle}"
        if len(line) > 200:
            print(f"{count}x {name} ({cost}){kw_part}:")
            print(f"  {oracle}")
        else:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
