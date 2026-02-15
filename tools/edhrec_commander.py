#!/usr/bin/env python3
"""
edhrec_commander.py — Fetch commander data from EDHREC using pyedhrec.

Retrieves deck counts, top/synergy/new cards, combos, average decklists,
and more for a specific commander.

Usage:
    python tools/edhrec_commander.py "Meren of Clan Nel Toth"
    python tools/edhrec_commander.py "Meren of Clan Nel Toth" --section high-synergy
    python tools/edhrec_commander.py "Korvold, Fae-Cursed King" --section combos
    python tools/edhrec_commander.py "Atraxa, Praetors' Voice" --section average-deck
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


def format_cardview(cv: dict, idx: int = 0) -> str:
    """Format a single EDHREC cardview dict into a readable line."""
    name = cv.get("name", "???")
    num_decks = cv.get("num_decks")
    potential = cv.get("potential_decks")
    synergy = cv.get("synergy")
    salt = cv.get("salt")

    parts = [f"{idx:>3}. {name}"]
    if num_decks is not None and potential:
        pct = (num_decks / potential) * 100 if potential > 0 else 0
        parts.append(f"({num_decks} decks, {pct:.0f}%)")
    elif num_decks is not None:
        parts.append(f"({num_decks} decks)")
    if synergy is not None:
        pct = synergy * 100 if abs(synergy) <= 1 else synergy
        parts.append(f"[synergy: {pct:+.0f}%]")
    if salt is not None:
        parts.append(f"[salt: {salt:.1f}]")
    return "  ".join(parts)


def format_card_list(card_list: dict, max_per_section: int = 15) -> str:
    """Format a dict of {header: [cardview, ...]} into readable text."""
    lines = []
    for header, cards in card_list.items():
        if not cards:
            continue
        lines.append(f"\n  ── {header} ──")
        for i, cv in enumerate(cards[:max_per_section], 1):
            lines.append(f"  {format_cardview(cv, i)}")
        if len(cards) > max_per_section:
            lines.append(f"  ... and {len(cards) - max_per_section} more")
    return "\n".join(lines)


def show_overview(edhrec: EDHRec, name: str):
    """Show general commander overview: deck count, top cards, key info."""
    print(f"Fetching EDHREC data for: {name} ...\n")

    try:
        data = edhrec.get_commander_data(name)
    except Exception as e:
        print(f"Error fetching commander data: {e}", file=sys.stderr)
        sys.exit(1)

    if not data:
        print(f"No data found for '{name}' on EDHREC.")
        sys.exit(1)

    # Header info
    container = data.get("container", {})
    json_dict = container.get("json_dict", {})
    card_info = json_dict.get("card", {})

    num_decks = card_info.get("num_decks") or json_dict.get("num_decks", "?")
    print(f"  Commander: {name}")
    print(f"  Decks on EDHREC: {num_decks}")
    link = edhrec.get_card_link(name)
    print(f"  EDHREC Page: {link}")
    print()

    # Show top cards
    try:
        top = edhrec.get_top_cards(name)
        if top:
            print(format_card_list(top, max_per_section=10))
    except Exception:
        pass

    # Show high synergy
    try:
        synergy = edhrec.get_high_synergy_cards(name)
        if synergy:
            print(format_card_list(synergy, max_per_section=10))
    except Exception:
        pass


def show_section(edhrec: EDHRec, name: str, section: str, max_cards: int = 20):
    """Show a specific section of commander data."""
    print(f"Fetching {section} for: {name} ...\n")

    section_map = {
        "high-synergy": ("get_high_synergy_cards", "High Synergy Cards"),
        "new": ("get_new_cards", "New Cards"),
        "top": ("get_top_cards", "Top Cards"),
        "creatures": ("get_top_creatures", "Top Creatures"),
        "instants": ("get_top_instants", "Top Instants"),
        "sorceries": ("get_top_sorceries", "Top Sorceries"),
        "enchantments": ("get_top_enchantments", "Top Enchantments"),
        "artifacts": ("get_top_artifacts", "Top Artifacts"),
        "mana-artifacts": ("get_top_mana_artifacts", "Top Mana Artifacts"),
        "planeswalkers": ("get_top_planeswalkers", "Top Planeswalkers"),
        "lands": ("get_top_lands", "Top Lands"),
        "utility-lands": ("get_top_utility_lands", "Top Utility Lands"),
        "battles": ("get_top_battles", "Top Battles"),
    }

    if section == "combos":
        try:
            combos = edhrec.get_card_combos(name)
            if not combos:
                print("No combos found.")
                return
            container = combos.get("container", {})
            combo_list = container.get("json_dict", {}).get("cardlists", [])
            if not combo_list:
                print("No combos found.")
                return
            for cl in combo_list:
                header = cl.get("header", "Combo")
                cards = cl.get("cardviews", [])
                print(f"  ── {header} ──")
                for cv in cards:
                    cname = cv.get("name", "?")
                    print(f"    • {cname}")
                print()
        except Exception as e:
            print(f"Error fetching combos: {e}", file=sys.stderr)
        return

    if section == "average-deck":
        try:
            deck_data = edhrec.get_commanders_average_deck(name)
            if not deck_data:
                print("No average deck found.")
                return
            decklist = deck_data.get("decklist", [])
            if not decklist:
                print("No average deck found.")
                return
            print(f"  Average Decklist for {name} ({len(decklist)} cards):\n")
            for entry in decklist:
                if isinstance(entry, dict):
                    cname = entry.get("name", "?")
                    print(f"  1 {cname}")
                elif isinstance(entry, str):
                    print(f"  1 {entry}")
        except Exception as e:
            print(f"Error fetching average deck: {e}", file=sys.stderr)
        return

    if section == "decks":
        try:
            decks = edhrec.get_commander_decks(name)
            if not decks:
                print("No decklists found.")
                return
            deck_list = decks if isinstance(decks, list) else decks.get("decks", [])
            if not deck_list:
                # Try different structure
                print("Decklist data structure:")
                if isinstance(decks, dict):
                    for key in list(decks.keys())[:5]:
                        print(f"  {key}: {type(decks[key])}")
                return
            for i, d in enumerate(deck_list[:10], 1):
                if isinstance(d, dict):
                    dname = d.get("name", d.get("title", "Unnamed"))
                    url = d.get("url", "")
                    print(f"  {i}. {dname}")
                    if url:
                        print(f"     {url}")
        except Exception as e:
            print(f"Error fetching decks: {e}", file=sys.stderr)
        return

    if section not in section_map:
        print(f"Unknown section: {section}", file=sys.stderr)
        print(f"Available: {', '.join(list(section_map.keys()) + ['combos', 'average-deck', 'decks'])}")
        sys.exit(1)

    method_name, label = section_map[section]
    try:
        method = getattr(edhrec, method_name)
        result = method(name)
        if result:
            print(format_card_list(result, max_per_section=max_cards))
        else:
            print(f"No {label.lower()} found.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch EDHREC data for a Commander.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Sections:
              overview (default), high-synergy, new, top, creatures, instants,
              sorceries, enchantments, artifacts, mana-artifacts, planeswalkers,
              lands, utility-lands, battles, combos, average-deck, decks
        """)
    )
    parser.add_argument("commander", nargs="+", help="Commander name")
    parser.add_argument("--section", "-s", type=str, default="overview",
                        help="Data section to show (default: overview)")
    parser.add_argument("--max", type=int, default=20, help="Max cards per section")

    args = parser.parse_args()
    commander_name = " ".join(args.commander)

    edhrec = EDHRec()

    if args.section == "overview":
        show_overview(edhrec, commander_name)
    else:
        show_section(edhrec, commander_name, args.section, max_cards=args.max)


if __name__ == "__main__":
    main()
