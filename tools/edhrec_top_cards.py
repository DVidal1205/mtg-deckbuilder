#!/usr/bin/env python3
"""
edhrec_top_cards.py — Get top/staple cards for a commander from EDHREC.

Fetches cards broken down by type: creatures, instants, sorceries,
enchantments, artifacts, lands, etc.

Usage:
    # All top cards for a commander
    python tools/edhrec_top_cards.py "Korvold, Fae-Cursed King"

    # Just top creatures
    python tools/edhrec_top_cards.py "Korvold, Fae-Cursed King" --type creatures --max 15

    # High synergy cards only
    python tools/edhrec_top_cards.py "Meren of Clan Nel Toth" --type high-synergy

    # New printings seeing play
    python tools/edhrec_top_cards.py "Atraxa, Praetors' Voice" --type new
"""

from __future__ import annotations

import argparse
import sys
import textwrap

try:
    from pyedhrec import EDHRec
except ImportError:
    print("Error: pyedhrec not installed. Run: pip install pyedhrec", file=sys.stderr)
    sys.exit(1)


TYPE_MAP = {
    "all": "get_commander_cards",
    "top": "get_top_cards",
    "high-synergy": "get_high_synergy_cards",
    "new": "get_new_cards",
    "creatures": "get_top_creatures",
    "instants": "get_top_instants",
    "sorceries": "get_top_sorceries",
    "enchantments": "get_top_enchantments",
    "artifacts": "get_top_artifacts",
    "mana-artifacts": "get_top_mana_artifacts",
    "planeswalkers": "get_top_planeswalkers",
    "lands": "get_top_lands",
    "utility-lands": "get_top_utility_lands",
    "battles": "get_top_battles",
}


def format_cardview(cv: dict, idx: int) -> str:
    """Format a cardview into a readable line."""
    name = cv.get("name", "???")
    num_decks = cv.get("num_decks")
    potential = cv.get("potential_decks")
    synergy = cv.get("synergy")

    parts = [f"{idx:>3}. {name}"]
    if num_decks is not None and potential:
        pct = (num_decks / potential) * 100 if potential > 0 else 0
        parts.append(f"({num_decks} decks, {pct:.0f}%)")
    elif num_decks is not None:
        parts.append(f"({num_decks} decks)")
    if synergy is not None:
        pct = synergy * 100 if abs(synergy) <= 1 else synergy
        parts.append(f"[synergy: {pct:+.0f}%]")
    return "  ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Get top/staple cards for a commander from EDHREC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Types:
              all (default), top, high-synergy, new, creatures, instants,
              sorceries, enchantments, artifacts, mana-artifacts,
              planeswalkers, lands, utility-lands, battles
        """)
    )
    parser.add_argument("commander", nargs="+", help="Commander name")
    parser.add_argument("--type", "-t", type=str, default="all",
                        choices=list(TYPE_MAP.keys()),
                        help="Card type/category to fetch (default: all)")
    parser.add_argument("--max", type=int, default=20,
                        help="Max cards per section (default: 20)")

    args = parser.parse_args()
    commander_name = " ".join(args.commander)

    edhrec = EDHRec()
    method_name = TYPE_MAP[args.type]
    method = getattr(edhrec, method_name)

    print(f"Fetching {args.type} cards for: {commander_name} ...\n")

    try:
        result = method(commander_name)
    except Exception as e:
        print(f"Error fetching data from EDHREC: {e}", file=sys.stderr)
        sys.exit(1)

    if not result:
        print(f"No results found for '{commander_name}'.")
        sys.exit(0)

    # result is a dict of {header: [cardview, ...]}
    total = 0
    for header, cards in result.items():
        if not cards:
            continue
        print(f"  ── {header} ──")
        for i, cv in enumerate(cards[:args.max], 1):
            print(f"  {format_cardview(cv, i)}")
            total += 1
        remaining = len(cards) - args.max
        if remaining > 0:
            print(f"  ... and {remaining} more")
        print()

    if total == 0:
        print("  No cards found.")


if __name__ == "__main__":
    main()
