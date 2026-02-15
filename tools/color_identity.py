#!/usr/bin/env python3
"""
color_identity.py — Browse cards and commanders by color identity.

Quick utility for Commander deckbuilding: find all cards or commanders
within a given color identity.

Usage:
    # All Simic commanders, sorted by popularity
    python tools/color_identity.py GU --commanders-only --sort edhrec_rank --max 30

    # All Boros cards with "exile" in oracle text
    python tools/color_identity.py RW --text exile --commander-legal

    # All colorless commanders
    python tools/color_identity.py C --commanders-only

    # All 5-color legendary creatures
    python tools/color_identity.py WUBRG --commanders-only
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import textwrap
from typing import Any, List, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cards.db")

WUBRG = set("WUBRG")

COLOR_NAMES = {
    "": "Colorless",
    "W": "White (Mono-White)",
    "U": "Blue (Mono-Blue)",
    "B": "Black (Mono-Black)",
    "R": "Red (Mono-Red)",
    "G": "Green (Mono-Green)",
    "WU": "Azorius (White-Blue)",
    "WB": "Orzhov (White-Black)",
    "WR": "Boros (White-Red)",
    "WG": "Selesnya (White-Green)",
    "UB": "Dimir (Blue-Black)",
    "UR": "Izzet (Blue-Red)",
    "UG": "Simic (Blue-Green)",
    "BR": "Rakdos (Black-Red)",
    "BG": "Golgari (Black-Green)",
    "RG": "Gruul (Red-Green)",
    "WUB": "Esper",
    "WUR": "Jeskai",
    "WUG": "Bant",
    "WBR": "Mardu",
    "WBG": "Abzan",
    "WRG": "Naya",
    "UBR": "Grixis",
    "UBG": "Sultai",
    "URG": "Temur",
    "BRG": "Jund",
    "WUBR": "Yore-Tiller (Sans Green)",
    "WUBG": "Witch-Maw (Sans Red)",
    "WURG": "Ink-Treader (Sans Black)",
    "WBRG": "Dune-Brood (Sans Blue)",
    "UBRG": "Glint-Eye (Sans White)",
    "WUBRG": "Five-Color",
}


def parse_colors(spec: str) -> List[str]:
    """Parse 'WUB' or 'W,U,B' or 'C' into sorted color list."""
    if spec.strip().upper() in ("C", "COLORLESS", ""):
        return []
    raw = spec.strip().upper().replace(",", "").replace(" ", "")
    return [c for c in "WUBRG" if c in raw]


def ci_subset_clause(allowed: List[str]) -> Tuple[str, List[Any]]:
    """Card's color_identity is a SUBSET of allowed."""
    if not allowed:
        return "(color_identity IS NULL OR color_identity = '')", []
    disallowed = [c for c in "WUBRG" if c not in allowed]
    if not disallowed:
        return "1=1", []
    parts = []
    params: List[Any] = []
    for c in disallowed:
        parts.append("color_identity NOT LIKE ?")
        params.append(f"%{c}%")
    return f"(color_identity IS NULL OR color_identity = '' OR ({' AND '.join(parts)}))", params


def format_card(row: dict, verbose: bool = False) -> str:
    name = row.get("name", "???")
    mana = row.get("mana_cost") or ""
    type_line = row.get("type_line") or ""
    ci = row.get("color_identity") or "C"
    rank = row.get("edhrec_rank")
    pt = ""
    if row.get("power") is not None and row.get("toughness") is not None:
        pt = f" [{row['power']}/{row['toughness']}]"
    rank_str = f"  (EDHREC #{rank})" if rank else ""
    header = f"{name}  {mana}  — {type_line}{pt}{rank_str}"

    if verbose:
        oracle = row.get("oracle_text") or ""
        if oracle:
            wrapped = textwrap.indent(textwrap.fill(oracle, width=76), "       ")
            return f"{header}\n{wrapped}"
    return header


def main():
    parser = argparse.ArgumentParser(
        description="Browse cards by color identity for Commander.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Color identity codes: W=White U=Blue B=Black R=Red G=Green C=Colorless
            Examples:
              %(prog)s GU --commanders-only --max 30
              %(prog)s RW --text exile --commander-legal
              %(prog)s C --commanders-only
              %(prog)s WUBRG --commanders-only --max 50
        """)
    )

    parser.add_argument("identity", type=str,
                        help="Color identity (e.g. 'GU', 'WBR', 'C' for colorless, 'WUBRG')")
    parser.add_argument("--commanders-only", action="store_true",
                        help="Only show legendary creatures (potential commanders)")
    parser.add_argument("--commander-legal", action="store_true",
                        help="Only Commander-legal cards")
    parser.add_argument("--text", type=str, help="Oracle text contains (case-insensitive)")
    parser.add_argument("--type", type=str, help="Type line contains")
    parser.add_argument("--keyword", type=str, help="Has keyword")
    parser.add_argument("--cmc-max", type=float, help="Maximum mana value")
    parser.add_argument("--max", type=int, default=30, help="Max results (default: 30)")
    parser.add_argument("--sort", type=str, default="edhrec_rank",
                        choices=["edhrec_rank", "cmc", "name"],
                        help="Sort by (default: edhrec_rank)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show oracle text")
    parser.add_argument("--db", type=str, default=DB_PATH, help=argparse.SUPPRESS)

    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    colors = parse_colors(args.identity)
    ci_key = "".join(colors) if colors else ""
    color_name = COLOR_NAMES.get(ci_key, ci_key or "Colorless")

    where: List[str] = []
    params: List[Any] = []

    # Color identity subset
    clause, ci_params = ci_subset_clause(colors)
    where.append(clause)
    params.extend(ci_params)

    # Commanders only
    if args.commanders_only:
        where.append("type_line LIKE '%Legendary%'")
        where.append("(type_line LIKE '%Creature%' OR oracle_text LIKE '%can be your commander%')")

    # Commander legal
    if args.commander_legal or args.commanders_only:
        where.append("legal_commander = 'legal'")

    # Text filter
    if args.text:
        where.append("(oracle_text LIKE ? OR face_oracle_texts LIKE ?)")
        params.append(f"%{args.text}%")
        params.append(f"%{args.text}%")

    # Type filter
    if args.type:
        where.append("type_line LIKE ?")
        params.append(f"%{args.type}%")

    # Keyword filter
    if args.keyword:
        where.append("keywords LIKE ?")
        params.append(f"%{args.keyword}%")

    # CMC filter
    if args.cmc_max is not None:
        where.append("cmc <= ?")
        params.append(args.cmc_max)

    where_sql = " AND ".join(where) if where else "1=1"

    sort_map = {
        "edhrec_rank": "edhrec_rank IS NULL, edhrec_rank ASC",
        "cmc": "cmc ASC",
        "name": "name ASC",
    }
    order = sort_map.get(args.sort, "edhrec_rank IS NULL, edhrec_rank ASC")

    sql = f"""
        SELECT name, mana_cost, cmc, type_line, oracle_text,
               power, toughness, loyalty, color_identity,
               edhrec_rank, keywords
        FROM cards
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ?
    """
    params.append(args.max)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    mode = "Commanders" if args.commanders_only else "Cards"
    print(f"\n{mode} within {color_name} identity ({len(rows)} results):\n")

    if not rows:
        print("  No cards found.")
        return

    for i, row in enumerate(rows, 1):
        r = dict(row)
        print(f"  {i:>3}. {format_card(r, verbose=args.verbose)}")
        if args.verbose:
            print()


if __name__ == "__main__":
    main()
