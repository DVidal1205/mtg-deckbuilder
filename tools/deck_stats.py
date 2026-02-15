#!/usr/bin/env python3
"""
deck_stats.py — Analyze a Commander decklist file.

Parses a decklist from .md or .txt format (see 06-output-format.md),
looks up every card in the local database, and outputs comprehensive stats:
mana curve, mana sources (lands + rocks), card types, category heuristics, and validation checks.

Supports two formats:
  - .md files: markdown with metadata + decklist inside a fenced code block
  - .txt files: plain card lines (N Card Name), one per line

Usage:
    python tools/deck_stats.py decks/meren-of-clan-nel-toth.md
    python tools/deck_stats.py decks/krenko-mob-boss.txt
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cards.db")

BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
               "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
               "Snow-Covered Mountain", "Snow-Covered Forest"}

# Mana cost: {W}, {U}, {B}, {R}, {G} and hybrid/physical like {U/R}, {2}, {C}
COST_SYMBOL_RE = re.compile(r'\{([WUBRG])(?:/([WUBRG2P]))?\}')

# Heuristic patterns for category estimation
RAMP_PATTERNS = [
    r"search your library for .{0,20}(?:land|forest|plains|island|swamp|mountain)",
    r"put .{0,30}land .{0,20}onto the battlefield",
    r"add \{",
    r"add one mana",
    r"add .{0,10} mana",
    r"costs? \{?\d*\}? less to cast",
]

DRAW_PATTERNS = [
    r"draw (?:a |two |three |\d+ )?card",
    r"draws? (?:a |two |three |\d+ )?card",
    r"look at the top .{0,20} put .{0,20} into your hand",
    r"reveal .{0,30} put .{0,20} into your hand",
]

REMOVAL_PATTERNS = [
    r"destroy target",
    r"exile target",
    r"(?:target|chosen) .{0,30} gets? -\d+/-\d+",
    r"deals? \d+ damage to (?:target|any target|any one target)",
    r"return target .{0,20} to .{0,10} owner",
]

WIPE_PATTERNS = [
    r"destroy all",
    r"exile all",
    r"(?:each|all) .{0,20}(?:creature|permanent|nonland).{0,20}(?:gets? -|destroy|exile|sacrifice|deals? \d+ damage)",
    r"deals? \d+ damage to each",
]

TUTOR_PATTERNS = [
    r"search your library for a card",
    r"search your library for .{0,30} card",
]

PROTECTION_PATTERNS = [
    r"(?:hexproof|shroud|indestructible|ward)",
    r"counter target .{0,20}spell",
    r"can't be (?:countered|blocked|the target)",
]


def parse_decklist(filepath: str) -> Tuple[Dict[str, str], List[Tuple[int, str]]]:
    """
    Parse a decklist file. Returns (metadata_dict, [(count, card_name), ...]).

    Supports two formats:

    1. Markdown (.md) — metadata in markdown, decklist in a fenced code block:
        # Deck Title
        | **Commander** | Meren of Clan Nel Toth |
        ## Decklist
        ```
        1 Card Name
        10 Swamp
        ```

    2. Plain text (.txt) — just card lines, no comments:
        1 Card Name
        10 Swamp
    """
    metadata: Dict[str, str] = {}
    cards: List[Tuple[int, str]] = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    is_md = filepath.lower().endswith(".md")

    if is_md:
        # Extract title from first # heading
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata["deck"] = title_match.group(1).strip()

        # Extract metadata from markdown table rows: | **Key** | Value |
        for m in re.finditer(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|', content):
            key = m.group(1).strip().lower()
            val = m.group(2).strip()
            metadata[key] = val

        # Extract card lines from fenced code blocks
        # Find all ``` blocks and look for card lines inside them
        fence_pattern = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)
        for fence_match in fence_pattern.finditer(content):
            block = fence_match.group(1)
            for line in block.strip().split("\n"):
                line = line.strip()
                card_match = re.match(r'^(\d+)\s+(.+)$', line)
                if card_match:
                    count = int(card_match.group(1))
                    name = card_match.group(2).strip()
                    cards.append((count, name))
    else:
        # Plain text: every non-empty line that matches "N Card Name"
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Skip comment lines (legacy format support)
            if line.startswith("//") or line.startswith("#"):
                continue
            card_match = re.match(r'^(\d+)\s+(.+)$', line)
            if card_match:
                count = int(card_match.group(1))
                name = card_match.group(2).strip()
                cards.append((count, name))

    return metadata, cards


def lookup_cards(conn: sqlite3.Connection, card_names: List[str]) -> Dict[str, dict]:
    """Look up card data for a list of names. Returns {name: row_dict}."""
    conn.row_factory = sqlite3.Row
    result = {}

    for name in card_names:
        row = conn.execute(
            "SELECT * FROM cards WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            result[name] = dict(row)
        else:
            # Try partial match
            row = conn.execute(
                "SELECT * FROM cards WHERE name LIKE ? COLLATE NOCASE LIMIT 1",
                (f"{name}%",)
            ).fetchone()
            if row:
                result[name] = dict(row)

    return result


def count_cost_colors(mana_cost: str) -> Counter:
    """Count colored symbols in a mana cost (how we SPEND mana). Each symbol counts: {U}{U} = 2 U, {2}{U}{R} = 1 U + 1 R; {U/R} = 0.5 each."""
    counts: Counter = Counter()
    if not mana_cost:
        return counts
    for m in COST_SYMBOL_RE.finditer(mana_cost):
        c1, c2 = m.group(1), m.group(2)
        if c2 and c2 in "WUBRG":  # hybrid/physical
            counts[c1] += 0.5
            counts[c2] += 0.5
        elif c1 in "WUBRG":
            counts[c1] += 1
    return counts


def colors_produced_by_card(card: dict, commander_ci: Optional[set] = None) -> set:
    """
    Return the set of colors (WUBRG) this card can produce as mana sources.
    Lands: produced_mana or oracle (Add {U}, fetch "Island or Mountain", etc.).
    Nonlands: oracle only, e.g. "Add {U}" or "Add one mana of any color".
    A dual land counts as a source for each color it produces.
    """
    colors = set()
    commander_ci = commander_ci or set()

    # 1. DB produced_mana (lands and some rocks have this)
    produced = (card.get("produced_mana") or "").strip().upper()
    if produced:
        for c in "WUBRG":
            if c in produced:
                colors.add(c)
        if colors:
            if commander_ci:
                colors = colors & commander_ci
            return colors

    oracle = (card.get("oracle_text") or "") + " " + (card.get("face_oracle_texts") or "")
    oracle_upper = oracle.upper()
    oracle_lower = oracle.lower()

    # 2. "Add {W}", "Add {U}", etc. (and "Add one mana of any color" → only count identity colors)
    if "ADD ONE MANA OF ANY COLOR" in oracle_upper:
        return set(commander_ci) if commander_ci else set("WUBRG")
    for c in "WUBRG":
        if f"ADD {{{c}}}" in oracle_upper:
            colors.add(c)
    if colors:
        return colors

    # 3. Commander's color identity (e.g. Command Tower, Arcane Signet)
    if "COMMANDER'S COLOR IDENTITY" in oracle_upper or "COLOR IDENTITY" in oracle_upper:
        return set(commander_ci) if commander_ci else set()

    # 4. Fetch lands: "search ... for ... Island or Mountain" — only count colors in identity
    if "SEARCH YOUR LIBRARY" in oracle_upper and "LAND" in oracle_lower:
        if "ISLAND" in oracle_upper:
            colors.add("U")
        if "MOUNTAIN" in oracle_upper:
            colors.add("R")
        if "PLAINS" in oracle_upper:
            colors.add("W")
        if "SWAMP" in oracle_upper:
            colors.add("B")
        if "FOREST" in oracle_upper:
            colors.add("G")

    # Restrict to deck's color identity so we don't count off-color (Strand→W, Delta→B, etc.)
    if commander_ci and colors:
        colors = colors & commander_ci
    return colors


def matches_patterns(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the regex patterns (case-insensitive)."""
    if not text:
        return False
    text_lower = text.lower()
    for pat in patterns:
        if re.search(pat, text_lower):
            return True
    return False


def categorize_card(card: dict) -> List[str]:
    """Heuristically categorize a card by its deckbuilding role(s)."""
    oracle = (card.get("oracle_text") or "") + " " + (card.get("face_oracle_texts") or "")
    categories = []

    if matches_patterns(oracle, RAMP_PATTERNS):
        categories.append("Ramp")
    if matches_patterns(oracle, DRAW_PATTERNS):
        categories.append("Card Draw")
    if matches_patterns(oracle, WIPE_PATTERNS):
        categories.append("Board Wipe")
    elif matches_patterns(oracle, REMOVAL_PATTERNS):
        categories.append("Removal")
    if matches_patterns(oracle, TUTOR_PATTERNS):
        categories.append("Tutor")
    if matches_patterns(oracle, PROTECTION_PATTERNS):
        categories.append("Protection")

    return categories


def get_primary_type(type_line: str) -> str:
    """Get the primary card type from a type line."""
    if not type_line:
        return "Unknown"
    tl = type_line.lower()
    if "land" in tl:
        return "Lands"
    if "creature" in tl:
        return "Creatures"
    if "instant" in tl:
        return "Instants"
    if "sorcery" in tl:
        return "Sorceries"
    if "enchantment" in tl:
        return "Enchantments"
    if "artifact" in tl:
        return "Artifacts"
    if "planeswalker" in tl:
        return "Planeswalkers"
    if "battle" in tl:
        return "Battles"
    return "Other"


def main():
    parser = argparse.ArgumentParser(description="Analyze a Commander decklist.")
    parser.add_argument("decklist", help="Path to the decklist file (.md or .txt)")
    parser.add_argument("--db", type=str, default=DB_PATH, help=argparse.SUPPRESS)

    args = parser.parse_args()

    if not os.path.exists(args.decklist):
        print(f"Error: Decklist not found: {args.decklist}", file=sys.stderr)
        sys.exit(1)

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    metadata, cards = parse_decklist(args.decklist)

    # Resolve total card count
    total_cards = sum(count for count, _ in cards)
    unique_names = [name for _, name in cards]

    # Look up cards in DB
    conn = sqlite3.connect(db_path)
    card_data = lookup_cards(conn, unique_names)

    # ── Header ──
    basename = os.path.basename(args.decklist)
    deck_name = metadata.get("deck", re.sub(r'\.(md|txt)$', '', basename))
    commander = metadata.get("commander", "Unknown")
    ci = metadata.get("color identity", "?")
    bracket = metadata.get("bracket", "?")

    print(f"\n{'=' * 60}")
    print(f"  Deck Stats: {deck_name}")
    print(f"{'=' * 60}")
    print(f"  Commander:      {commander}")
    print(f"  Color Identity: {ci}")
    if bracket != "?":
        print(f"  Bracket:        {bracket}")
    print()

    # ── Card Count ──
    check = "✓" if total_cards == 100 else f"✗ ({total_cards})"
    print(f"  Card Count: {total_cards} ({check})")

    # ── Type breakdown ──
    type_counts: Counter = Counter()
    land_count = 0
    nonland_count = 0

    for count, name in cards:
        data = card_data.get(name, {})
        ptype = get_primary_type(data.get("type_line", ""))
        type_counts[ptype] += count
        if ptype == "Lands":
            land_count += count
        else:
            nonland_count += count

    commander_count = 1  # The commander is one of the nonlands
    print(f"  Lands: {land_count} | Nonlands: {nonland_count - commander_count} + Commander")
    print()

    # ── Mana Curve ──
    curve: Counter = Counter()
    total_mv = 0.0
    nonland_nonzero_count = 0

    for count, name in cards:
        data = card_data.get(name, {})
        ptype = get_primary_type(data.get("type_line", ""))
        if ptype == "Lands":
            continue
        cmc = data.get("cmc")
        if cmc is None:
            continue
        cmc_int = int(cmc)
        if cmc_int >= 7:
            cmc_int = 7  # 7+ bucket
        curve[cmc_int] += count
        total_mv += cmc * count
        nonland_nonzero_count += count

    avg_mv = total_mv / nonland_nonzero_count if nonland_nonzero_count else 0

    print("  Mana Curve (nonland):")
    max_bar = max(curve.values()) if curve else 1
    for mv in range(0, 8):
        c = curve.get(mv, 0)
        bar = "█" * int((c / max_bar) * 20) if max_bar > 0 else ""
        label = "7+" if mv == 7 else str(mv)
        print(f"    {label:>2}: {bar:<20s} {c}")
    print(f"  Average MV: {avg_mv:.2f}")
    print()

    # ── Mana sources (lands + nonlands that produce mana: "Add {U}", etc.) ──
    # Each land or rock counts as 1 source per color it can produce; dual = 1 per color.
    commander_ci_raw = metadata.get("color identity", "") or ""
    commander_ci = set(c.strip().upper() for c in commander_ci_raw.replace(",", "").split() if c.strip() in "WUBRG")
    if not commander_ci and commander_ci_raw:
        commander_ci = set(c.upper() for c in commander_ci_raw if c.upper() in "WUBRG")

    source_count: Counter = Counter()
    for count, name in cards:
        data = card_data.get(name, {})
        produced = colors_produced_by_card(data, commander_ci)
        for c in produced:
            source_count[c] += count

    if source_count:
        # Only show colors in deck's identity (so 2-color deck doesn't show 0% W/B/G from fetches)
        show_colors = commander_ci if commander_ci else set(source_count.keys())
        total_sources = sum(source_count[c] for c in show_colors)
        color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        print("  Mana sources (lands + rocks / Add mana):")
        for color in "WUBRG":
            if color in show_colors and source_count.get(color, 0) > 0:
                n = source_count[color]
                pct = (n / total_sources) * 100 if total_sources else 0
                print(f"    {color_names[color]:8s}: {n} sources  ({pct:.1f}%)")
        print()

    # ── Mana costs (spending): colored symbols in nonland casting costs ──
    cost_count: Counter = Counter()
    for count, name in cards:
        data = card_data.get(name, {})
        ptype = get_primary_type(data.get("type_line", ""))
        if ptype == "Lands":
            continue
        mana_cost = data.get("mana_cost") or ""
        for c, n in count_cost_colors(mana_cost).items():
            cost_count[c] += n * count

    if cost_count:
        show_cost_colors = commander_ci if commander_ci else set(cost_count.keys())
        total_cost = sum(cost_count[c] for c in show_cost_colors)
        color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        print("  Mana costs (spending) — colored symbols in nonland costs:")
        for color in "WUBRG":
            if color in show_cost_colors and cost_count.get(color, 0) > 0:
                n = cost_count[color]
                pct = (n / total_cost) * 100 if total_cost else 0
                print(f"    {color_names[color]:8s}: {n} symbols  ({pct:.1f}%)")
        print()

    # ── Card Types ──
    print("  Card Types:")
    for ptype in ["Creatures", "Instants", "Sorceries", "Enchantments",
                   "Artifacts", "Planeswalkers", "Battles", "Lands", "Other"]:
        c = type_counts.get(ptype, 0)
        if c > 0:
            print(f"    {ptype:16s} {c}")
    print()

    # ── Category Estimates ──
    cat_counts: Counter = Counter()
    for count, name in cards:
        data = card_data.get(name, {})
        ptype = get_primary_type(data.get("type_line", ""))
        if ptype == "Lands":
            continue
        cats = categorize_card(data)
        for cat in cats:
            cat_counts[cat] += count

    print("  Category Estimates (heuristic):")
    for cat in ["Ramp", "Card Draw", "Removal", "Board Wipe", "Tutor", "Protection"]:
        c = cat_counts.get(cat, 0)
        if c > 0:
            print(f"    {cat:16s} ~{c}")
    print()

    # ── Singleton Check ──
    name_counts: Counter = Counter()
    for count, name in cards:
        name_counts[name] += count

    duplicates = [(name, c) for name, c in name_counts.items()
                  if c > 1 and name not in BASIC_LANDS]
    if duplicates:
        print(f"  Singleton Check: ✗ Duplicates found:")
        for name, c in duplicates:
            print(f"    {name} (×{c})")
    else:
        print("  Singleton Check: ✓ No duplicates (excluding basics)")

    # ── Color Identity Check ──
    ci_violations = []
    commander_data = card_data.get(commander, {})
    commander_ci_raw = commander_data.get("color_identity") or ""
    commander_ci = set(c.strip() for c in commander_ci_raw.split(",") if c.strip())

    if commander_ci or commander_ci_raw == "":
        for count, name in cards:
            data = card_data.get(name, {})
            card_ci_raw = data.get("color_identity") or ""
            card_ci = set(c.strip() for c in card_ci_raw.split(",") if c.strip())
            if not card_ci.issubset(commander_ci):
                ci_violations.append((name, card_ci))

    if ci_violations:
        ci_display = ",".join(sorted(commander_ci)) if commander_ci else "C"
        print(f"  Color Identity Check: ✗ {len(ci_violations)} violation(s) (commander CI: {ci_display}):")
        for name, card_ci in ci_violations[:10]:
            print(f"    {name} (CI: {','.join(sorted(card_ci))})")
    else:
        ci_display = ",".join(sorted(commander_ci)) if commander_ci else "C"
        print(f"  Color Identity Check: ✓ All cards within {ci_display}")

    # ── Commander Legality Check ──
    illegal = []
    for count, name in cards:
        data = card_data.get(name, {})
        legality = data.get("legal_commander", "")
        if legality and legality != "legal":
            illegal.append((name, legality))

    not_found = [name for _, name in cards if name not in card_data]

    if illegal:
        print(f"  Commander Legality: ✗ {len(illegal)} illegal card(s):")
        for name, status in illegal:
            print(f"    {name} ({status})")
    else:
        print("  Commander Legality: ✓ All cards legal in Commander")

    if not_found:
        print(f"\n  ⚠ {len(not_found)} card(s) not found in database:")
        for name in not_found[:10]:
            print(f"    {name}")
        if len(not_found) > 10:
            print(f"    ... and {len(not_found) - 10} more")

    print(f"\n{'=' * 60}")
    conn.close()


if __name__ == "__main__":
    main()
