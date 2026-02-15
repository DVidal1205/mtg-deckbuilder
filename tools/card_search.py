#!/usr/bin/env python3
"""
card_search.py — Flexible card search against the local Scryfall SQLite database.

Supports structured filters, multi-pattern oracle text (OR'd), FTS5 full-text
search, and "cards like X" discovery. Designed for Commander deckbuilding.

Usage examples:
    # Basic structured search
    python tools/card_search.py --type creature --keyword flying --cmc-max 3 --color-identity UW

    # Multi-pattern oracle text (OR'd together)
    python tools/card_search.py --text "when a creature dies" "whenever a creature you control dies" --color-identity BG

    # FTS5 full-text search (supports FTS5 syntax: AND, OR, NEAR, NOT, "phrases")
    python tools/card_search.py --fts "sacrifice NEAR creature" --color-identity BG --commander-legal

    # Game changers only (DB list; B3 max 3)
    python tools/card_search.py --game-changer --commander-legal

    # Find cards similar to a known card
    python tools/card_search.py --like "Grave Pact" --color-identity BG

    # Commander search
    python tools/card_search.py --is-commander --color-identity GU --sort edhrec_rank --max 20

    # Raw SQL escape hatch
    python tools/card_search.py --sql "oracle_text LIKE '%annihilator%'" --commander-legal
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import textwrap
from typing import Any, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cards.db")

# ── Helpers ──────────────────────────────────────────────────────────────────

WUBRG = set("WUBRG")


def parse_colors(spec: str) -> List[str]:
    """Parse 'WUB' or 'W,U,B' into ['W','U','B']."""
    raw = spec.strip().upper().replace(",", "").replace(" ", "")
    return [c for c in raw if c in WUBRG]


def ci_subset_clause(allowed: List[str]) -> Tuple[str, List[Any]]:
    """
    SQL clause: card's color_identity is a SUBSET of `allowed`.
    color_identity is stored as comma-separated TEXT (e.g. 'W,U') or NULL/'' for colorless.
    Colorless cards are always included.
    """
    if not allowed:
        # Only colorless cards
        return "(color_identity IS NULL OR color_identity = '')", []

    disallowed = [c for c in "WUBRG" if c not in allowed]
    if not disallowed:
        # All 5 colors allowed — no restriction
        return "1=1", []

    parts = []
    params: List[Any] = []
    for c in disallowed:
        parts.append("color_identity NOT LIKE ?")
        params.append(f"%{c}%")

    clause = " AND ".join(parts)
    return f"(color_identity IS NULL OR color_identity = '' OR ({clause}))", params


def format_card(row: dict, verbose: bool = False) -> str:
    """Format a card row into a concise human-readable summary."""
    name = row.get("name", "???")
    mana = row.get("mana_cost") or ""
    cmc = row.get("cmc")
    type_line = row.get("type_line") or ""
    ci = row.get("color_identity") or "C"
    rank = row.get("edhrec_rank")
    pt = ""
    if row.get("power") is not None and row.get("toughness") is not None:
        pt = f" [{row['power']}/{row['toughness']}]"
    loyalty = ""
    if row.get("loyalty"):
        loyalty = f" [Loyalty: {row['loyalty']}]"

    rank_str = f"  (EDHREC #{rank})" if rank else ""
    gc_str = "  [game changer]" if row.get("game_changer") == 1 else ""
    header = f"{name}  {mana}  — {type_line}{pt}{loyalty}{rank_str}{gc_str}"

    if verbose:
        oracle = row.get("oracle_text") or row.get("face_oracle_texts") or ""
        if oracle:
            wrapped = textwrap.indent(textwrap.fill(oracle, width=80), "    ")
            return f"{header}\n{wrapped}"
    return header


# ── Query builder ────────────────────────────────────────────────────────────

def build_query(args: argparse.Namespace) -> Tuple[str, List[Any]]:
    """Build the SELECT query from parsed CLI args."""
    use_fts = bool(args.fts)
    where: List[str] = []
    params: List[Any] = []

    # FTS5 full-text search
    if args.fts:
        where.append("cards_fts MATCH ?")
        params.append(args.fts)

    # Name contains
    if args.name:
        where.append("c.name LIKE ?")
        params.append(f"%{args.name}%")

    # Color identity (Commander subset check)
    if args.color_identity:
        allowed = parse_colors(args.color_identity)
        clause, ci_params = ci_subset_clause(allowed)
        # Prefix with table alias
        clause = clause.replace("color_identity", "c.color_identity")
        where.append(clause)
        params.extend(ci_params)

    # Exact colors
    if args.colors:
        cols = parse_colors(args.colors)
        for c in cols:
            where.append("c.colors LIKE ?")
            params.append(f"%{c}%")

    # Type line contains
    if args.type:
        where.append("c.type_line LIKE ?")
        params.append(f"%{args.type}%")

    # Oracle text — multiple patterns OR'd together
    if args.text:
        text_clauses = []
        for pattern in args.text:
            text_clauses.append("(c.oracle_text LIKE ? OR c.face_oracle_texts LIKE ?)")
            params.append(f"%{pattern}%")
            params.append(f"%{pattern}%")
        where.append(f"({' OR '.join(text_clauses)})")

    # CMC range
    if args.cmc_min is not None:
        where.append("c.cmc >= ?")
        params.append(args.cmc_min)
    if args.cmc_max is not None:
        where.append("c.cmc <= ?")
        params.append(args.cmc_max)

    # Power/toughness range
    if args.power_min is not None:
        where.append("CAST(c.power AS REAL) >= ?")
        params.append(args.power_min)
    if args.power_max is not None:
        where.append("CAST(c.power AS REAL) <= ?")
        params.append(args.power_max)
    if args.toughness_min is not None:
        where.append("CAST(c.toughness AS REAL) >= ?")
        params.append(args.toughness_min)
    if args.toughness_max is not None:
        where.append("CAST(c.toughness AS REAL) <= ?")
        params.append(args.toughness_max)

    # Keyword
    if args.keyword:
        kw_clauses = []
        for kw in args.keyword:
            kw_clauses.append("c.keywords LIKE ?")
            params.append(f"%{kw}%")
        where.append(f"({' OR '.join(kw_clauses)})")

    # Mechanic tag
    if args.tag:
        tag_clauses = []
        for t in args.tag:
            tag_clauses.append("c.mechanic_tags LIKE ?")
            params.append(f"%{t}%")
        where.append(f"({' OR '.join(tag_clauses)})")

    # Rarity
    if args.rarity:
        where.append("c.rarity = ?")
        params.append(args.rarity.lower())

    # Commander legal
    if args.commander_legal:
        where.append("c.legal_commander = 'legal'")

    # Game changer (DB has literal list: game_changer = 1)
    if getattr(args, "game_changer", False):
        where.append("c.game_changer = 1")
    if getattr(args, "no_game_changer", False):
        where.append("(c.game_changer IS NULL OR c.game_changer = 0)")

    # Is commander (legendary creature)
    if args.is_commander:
        where.append("c.type_line LIKE '%Legendary%'")
        where.append("(c.type_line LIKE '%Creature%' OR c.oracle_text LIKE '%can be your commander%')")

    # Raw SQL escape hatch
    if args.sql:
        where.append(f"({args.sql})")

    where_sql = " AND ".join(where) if where else "1=1"

    # Sort
    sort_map = {
        "edhrec_rank": "c.edhrec_rank",
        "cmc": "c.cmc",
        "name": "c.name",
        "power": "CAST(c.power AS REAL)",
    }
    order_col = sort_map.get(args.sort, "c.edhrec_rank")
    order_dir = "DESC" if args.sort_dir and args.sort_dir.upper() == "DESC" else "ASC"

    # Handle NULL edhrec_rank: push nulls to the end
    if args.sort == "edhrec_rank" or args.sort is None:
        order_clause = f"{order_col} IS NULL, {order_col} {order_dir}"
    else:
        order_clause = f"{order_col} {order_dir}"

    select_cols = """
        c.name, c.mana_cost, c.cmc, c.type_line, c.oracle_text,
        c.face_oracle_texts, c.power, c.toughness, c.loyalty,
        c.colors, c.color_identity, c.keywords, c.mechanic_tags,
        c.rarity, c.edhrec_rank, c.legal_commander, c.game_changer
    """

    fts_join = "JOIN cards_fts ON cards_fts.rowid = c.rowid" if use_fts else ""

    sql = f"""
        SELECT {select_cols}
        FROM cards c
        {fts_join}
        WHERE {where_sql}
        ORDER BY {order_clause}
        LIMIT ?
    """
    params.append(args.max)

    return sql, params


# ── "Like" discovery ─────────────────────────────────────────────────────────

def find_similar(db_path: str, card_name: str, args: argparse.Namespace) -> List[dict]:
    """
    Find cards similar to `card_name` by matching keywords, type-line tokens,
    and mechanic tags. Results are scored by how many attributes overlap.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Look up the source card
    row = conn.execute(
        "SELECT * FROM cards WHERE name = ? COLLATE NOCASE", (card_name,)
    ).fetchone()

    if not row:
        # Try partial match
        row = conn.execute(
            "SELECT * FROM cards WHERE name LIKE ? COLLATE NOCASE ORDER BY edhrec_rank ASC LIMIT 1",
            (f"%{card_name}%",)
        ).fetchone()

    if not row:
        conn.close()
        return []

    source = dict(row)
    source_name = source["name"]

    # Extract similarity features
    keywords_raw = source.get("keywords") or ""
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    tags_raw = source.get("mechanic_tags") or ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    type_line = source.get("type_line") or ""
    # Extract meaningful type words (skip supertypes and generic types)
    skip_types = {"Legendary", "Basic", "Snow", "World", "Ongoing", "—", "Creature",
                  "Artifact", "Enchantment", "Instant", "Sorcery", "Planeswalker",
                  "Land", "Battle", "Tribal", "Kindred"}
    type_tokens = [t for t in type_line.split() if t not in skip_types and len(t) > 2]

    if not keywords and not tags and not type_tokens:
        conn.close()
        return []

    # Build a scoring query using CASE WHEN for each feature
    score_parts: List[str] = []
    params: List[Any] = []

    for kw in keywords[:8]:  # cap to avoid huge queries
        score_parts.append("(CASE WHEN c.keywords LIKE ? THEN 2 ELSE 0 END)")
        params.append(f"%{kw}%")

    for tag in tags[:8]:
        score_parts.append("(CASE WHEN c.mechanic_tags LIKE ? THEN 3 ELSE 0 END)")
        params.append(f"%{tag}%")

    for tt in type_tokens[:5]:
        score_parts.append("(CASE WHEN c.type_line LIKE ? THEN 1 ELSE 0 END)")
        params.append(f"%{tt}%")

    score_expr = " + ".join(score_parts) if score_parts else "0"

    # Apply color identity filter if specified
    ci_clause = "1=1"
    ci_params: List[Any] = []
    if args.color_identity:
        allowed = parse_colors(args.color_identity)
        ci_clause, ci_params = ci_subset_clause(allowed)
        ci_clause = ci_clause.replace("color_identity", "c.color_identity")

    legal_clause = "c.legal_commander = 'legal'" if args.commander_legal else "1=1"

    sql = f"""
        SELECT c.name, c.mana_cost, c.cmc, c.type_line, c.oracle_text,
               c.face_oracle_texts, c.power, c.toughness, c.loyalty,
               c.colors, c.color_identity, c.keywords, c.mechanic_tags,
               c.rarity, c.edhrec_rank, c.legal_commander,
               ({score_expr}) AS similarity_score
        FROM cards c
        WHERE c.name != ?
          AND ({ci_clause})
          AND {legal_clause}
          AND ({score_expr}) > 0
        ORDER BY similarity_score DESC, c.edhrec_rank IS NULL, c.edhrec_rank ASC
        LIMIT ?
    """
    # params has score params already; we need them twice (once for SELECT, once for WHERE)
    all_params = params + [source_name] + ci_params + params + [args.max]

    rows = conn.execute(sql, all_params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Search the local MTG card database for Commander deckbuilding.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s --type creature --keyword flying --cmc-max 3 --color-identity UW
              %(prog)s --text "when a creature dies" "sacrifice a creature" --color-identity BG
              %(prog)s --fts "exile NEAR graveyard" --commander-legal
              %(prog)s --like "Grave Pact" --color-identity BG --commander-legal
              %(prog)s --is-commander --color-identity GU --sort edhrec_rank --max 20
        """)
    )

    # Structured filters
    parser.add_argument("--name", type=str, help="Card name contains (case-insensitive)")
    parser.add_argument("--color-identity", type=str, metavar="CI",
                        help="Within this color identity for Commander (e.g. 'WUB', 'GR')")
    parser.add_argument("--colors", type=str, help="Card has these colors (e.g. 'UB')")
    parser.add_argument("--type", type=str, help="Type line contains (e.g. 'creature', 'enchantment')")
    parser.add_argument("--text", nargs="+", metavar="PATTERN",
                        help="Oracle text contains ANY of these patterns (OR'd). Supports multiple.")
    parser.add_argument("--fts", type=str, metavar="QUERY",
                        help="FTS5 full-text search (supports AND, OR, NEAR, NOT, \"phrases\")")
    parser.add_argument("--cmc-min", type=float, help="Minimum mana value")
    parser.add_argument("--cmc-max", type=float, help="Maximum mana value")
    parser.add_argument("--power-min", type=float, help="Minimum power")
    parser.add_argument("--power-max", type=float, help="Maximum power")
    parser.add_argument("--toughness-min", type=float, help="Minimum toughness")
    parser.add_argument("--toughness-max", type=float, help="Maximum toughness")
    parser.add_argument("--keyword", nargs="+", metavar="KW",
                        help="Has keyword (e.g. flying, deathtouch). Multiple = OR.")
    parser.add_argument("--tag", nargs="+", metavar="TAG",
                        help="Has mechanic tag (e.g. blink, aristocrats). Multiple = OR.")
    parser.add_argument("--rarity", type=str, choices=["common", "uncommon", "rare", "mythic"],
                        help="Rarity filter")
    parser.add_argument("--commander-legal", action="store_true", help="Only Commander-legal cards")
    parser.add_argument("--game-changer", action="store_true",
                        help="Only cards on the DB game-changers list (B3 limit: max 3)")
    parser.add_argument("--no-game-changer", action="store_true",
                        help="Exclude cards on the DB game-changers list")
    parser.add_argument("--is-commander", action="store_true",
                        help="Only legendary creatures (potential commanders)")

    # Discovery
    parser.add_argument("--like", type=str, metavar="CARD",
                        help="Find cards similar to this card (by keywords, types, mechanic tags)")

    # Output control
    parser.add_argument("--max", type=int, default=20, help="Max results (default: 20)")
    parser.add_argument("--sort", type=str, default="edhrec_rank",
                        choices=["edhrec_rank", "cmc", "name", "power"],
                        help="Sort by field (default: edhrec_rank)")
    parser.add_argument("--sort-dir", type=str, default="ASC", choices=["ASC", "DESC"],
                        help="Sort direction (default: ASC)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show full oracle text for each card")
    parser.add_argument("--sql", type=str, metavar="WHERE",
                        help="Raw SQL WHERE clause (escape hatch)")
    parser.add_argument("--db", type=str, default=DB_PATH, help=argparse.SUPPRESS)

    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        print("Run: python utils/csv_to_sqlite.py data/cards.csv data/cards.db", file=sys.stderr)
        sys.exit(1)

    if getattr(args, "game_changer", False) and getattr(args, "no_game_changer", False):
        print("Error: --game-changer and --no-game-changer are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    # ── "Like" mode ──
    if args.like:
        results = find_similar(db_path, args.like, args)
        if not results:
            print(f"No similar cards found for '{args.like}'.")
            sys.exit(0)
        print(f"Cards similar to '{args.like}' ({len(results)} results):\n")
        for i, row in enumerate(results, 1):
            score = row.get("similarity_score", "")
            score_str = f"  [sim: {score}]" if score else ""
            print(f"  {i:>3}. {format_card(row, verbose=args.verbose)}{score_str}")
            if args.verbose:
                print()
        sys.exit(0)

    # ── Standard search mode ──
    sql, params = build_query(args)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"Query error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    if not rows:
        print("No cards found matching your criteria.")
        sys.exit(0)

    print(f"Found {len(rows)} card(s):\n")
    for i, row in enumerate(rows, 1):
        r = dict(row)
        print(f"  {i:>3}. {format_card(r, verbose=args.verbose)}")
        if args.verbose:
            print()


if __name__ == "__main__":
    main()
