"""
search_cards.py

A small, ADK-friendly search module for your local MTG SQLite database.

Design goals:
- Pure Python functions (no CLI), easy to register as Google ADK tools.
- Supports:
  - Full-text search (FTS5) across name/type_line/oracle_text/face_oracle_texts
  - Structured filters: name, types, cmc range, colors, color identity (commander subset),
    legalities, set, rarity, prices, keywords, and your mechanic_tags column.
- Returns: list[dict] rows (JSON-serializable) suitable for LLM agent consumption.

Important notes:
- FTS5 only indexes a subset of columns. When you want fields like mana_cost or prices,
  we JOIN cards_fts back to cards.
- SQLite FTS5 MATCH cannot reference an alias; it must reference `cards_fts` explicitly.
- Commander legality is best enforced via Scryfall `color_identity`. This module uses
  a robust subset check against your comma-separated `color_identity` string. In the
  future, a bitmask column will be faster and perfectly precise.

Example usage:

    from utils.search_cards import search_cards

    results = search_cards(
        db_path="data/cards.db",
        text_query='"return it to the battlefield"',
        commander_ci="UW",
        legal_format="commander",
        cmc_max=4,
        price_usd_max=5.0,
        mechanic_tags_any=["blink"],
        limit=25,
        order_by="edhrec_rank",
    )

    # results is a list[dict] with card fields
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ----------------------------
# Helpers
# ----------------------------


def parse_colors(colors: Optional[str]) -> List[str]:
    """
    Parse color spec into a list of single-letter color codes.

    Accepts:
      - "U,W"  -> ["U","W"]
      - "UW"   -> ["U","W"]
      - "U W"  -> ["U","W"]

    Returns:
      List[str] of colors in WUBRG alphabet; duplicates removed.
    """
    if not colors:
        return []
    raw = colors.strip().upper().replace(" ", "").replace(",", "")
    out = []
    for c in raw:
        if c in "WUBRG" and c not in out:
            out.append(c)
    return out


def _like_any(field_sql: str, needles: Sequence[str]) -> Tuple[str, List[Any]]:
    """
    Build a SQL clause that matches if field contains ANY needle.

    Example:
      _like_any("c.type_line", ["Creature","Artifact"])
      -> ("(c.type_line LIKE ? OR c.type_line LIKE ?)", ["%Creature%","%Artifact%"])
    """
    if not needles:
        return "1=1", []
    clauses = []
    params: List[Any] = []
    for n in needles:
        clauses.append(f"{field_sql} LIKE ?")
        params.append(f"%{n}%")
    return "(" + " OR ".join(clauses) + ")", params


def _ci_subset_clause(ci_col_sql: str, allowed_ci: Sequence[str]) -> Tuple[str, List[Any]]:
    """
    Build a clause enforcing that card's color_identity is a subset of allowed_ci.

    Assumes `color_identity` is stored as a comma-separated string containing only W/U/B/R/G,
    e.g. "U,W" or ""/NULL for colorless.

    Logic:
      - colorless (NULL or '') is always allowed
      - any disallowed color must not appear in the color_identity string

    Returns:
      (sql_clause, params)

    Note:
      This is correct given Scryfall's `color_identity` encoding. A bitmask column would
      be faster, but this is robust and works now.
    """
    allowed = set(allowed_ci)
    disallowed = [c for c in "WUBRG" if c not in allowed]

    if not allowed_ci:
        # Only allow colorless
        return f"({ci_col_sql} IS NULL OR {ci_col_sql} = '')", []

    clauses = []
    params: List[Any] = []

    # Colorless allowed
    # For non-colorless, enforce NOT LIKE for each disallowed color.
    base = f"({ci_col_sql} IS NULL OR {ci_col_sql} = '')"
    for c in disallowed:
        clauses.append(f"({ci_col_sql} NOT LIKE ?)")
        params.append(f"%{c}%")

    if clauses:
        return f"({base} OR (" + " AND ".join(clauses) + "))", params
    return f"({base} OR 1=1)", []


def _legal_col(format_name: str) -> str:
    """
    Convert 'commander' -> c."legal_commander" (quoted for safety).
    """
    fmt = format_name.strip().lower()
    if not fmt:
        raise ValueError("legal_format must be a non-empty string")
    return f'c."legal_{fmt}"'


# ----------------------------
# Public API
# ----------------------------


@dataclass(frozen=True)
class CardSearchFilters:
    """
    Strongly-typed container for optional search filters.

    You can pass None for any filter to ignore it.

    Fields:
      text_query:
        If provided, uses FTS5 to match across:
          - name
          - type_line
          - oracle_text
          - face_oracle_texts

        This is the best way to do "oracle text" searching.

      name_contains:
        Case-insensitive substring match on cards.name (LIKE %...%).

      type_contains_any:
        List of substrings that should appear in type_line (OR).
        Example: ["Creature", "Artifact"].

      oracle_contains:
        Optional substring match directly against oracle_text (LIKE).
        Usually you want text_query instead, but this can be handy for simple filters.

      cmc_min / cmc_max:
        Numeric mana value range (inclusive).

      colors_any:
        Matches cards.colors containing ANY of these color letters.
        (This is NOT commander legality; it's the printed colors list.)

      commander_ci:
        Enforces Commander color identity: card.color_identity must be subset of commander_ci.
        Accepts "UW" or "U,W".

      legal_format / legal_value:
        Example: legal_format="commander", legal_value="legal"
        Filters on column c."legal_commander" = "legal"

      rarity:
        Exact match (common/uncommon/rare/mythic/special)

      set_code:
        Exact match on c."set" (Scryfall set code).

      price_usd_max:
        Requires c.price_usd <= price_usd_max (and non-null).

      keywords_any:
        Matches cards.keywords containing ANY of the provided terms (comma-separated string from Scryfall).
        Example: ["Flying","Vigilance"].

      mechanic_tags_any:
        Matches your custom c.mechanic_tags column (comma-separated) containing ANY of these tags.
        Example: ["blink","aristocrats"].

      limit / offset:
        Pagination.

      order_by / order_dir:
        Sort results. Supported order_by:
          - "edhrec_rank"
          - "cmc"
          - "price_usd"
          - "name"
          - "released_at"
        order_dir: "ASC" or "DESC"
    """

    text_query: Optional[str] = None
    name_contains: Optional[str] = None
    type_contains_any: Optional[Sequence[str]] = None
    oracle_contains: Optional[str] = None

    cmc_min: Optional[float] = None
    cmc_max: Optional[float] = None

    colors_any: Optional[str] = None
    commander_ci: Optional[str] = None

    legal_format: Optional[str] = None
    legal_value: str = "legal"

    rarity: Optional[str] = None
    set_code: Optional[str] = None
    price_usd_max: Optional[float] = None

    keywords_any: Optional[Sequence[str]] = None
    mechanic_tags_any: Optional[Sequence[str]] = None

    limit: int = 50
    offset: int = 0
    order_by: str = "edhrec_rank"
    order_dir: str = "ASC"


def search_cards(
    db_path: str,
    filters: Optional[CardSearchFilters] = None,
    *,
    select_fields: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search the MTG cards database with optional FTS5 + structured filters.

    This is intended to be used as an ADK tool function:
      - pure function signature (db_path + params)
      - returns JSON-serializable objects
      - docstrings describe behavior clearly

    Args:
      db_path:
        Path to the SQLite database file created by csv_to_sqlite.py.

      filters:
        CardSearchFilters object (or None to return a default sample page).
        If filters.text_query is provided, an FTS JOIN is used:
          JOIN cards_fts ON cards_fts.rowid = c.rowid
          WHERE cards_fts MATCH ?

      select_fields:
        Optional list of columns to return from cards.
        If None, a reasonable default set is returned.

        Note:
          These should be column names in the `cards` table (not cards_fts),
          e.g. ["id","name","mana_cost","oracle_text","color_identity",...].

    Returns:
      List[Dict[str, Any]] where each dict is a row of selected card fields.

    Raises:
      sqlite3.Error if SQL execution fails.
      ValueError for invalid filter arguments (e.g. empty legal_format).
    """
    f = filters or CardSearchFilters()

    # Default fields: enough for deckbuilding and UI.
    default_fields = [
        "id",
        "name",
        "mana_cost",
        "cmc",
        "type_line",
        "oracle_text",
        "colors",
        "color_identity",
        "rarity",
        "edhrec_rank",
        "price_usd",
        "set",
        "set_name",
        "legal_commander",
        "keywords",
        "mechanic_tags",
        "image_normal",
        "scryfall_uri",
    ]
    fields = list(select_fields) if select_fields else default_fields

    # Whitelist ordering (avoid SQL injection via order_by)
    order_map = {
        "edhrec_rank": "c.edhrec_rank",
        "cmc": "c.cmc",
        "price_usd": "c.price_usd",
        "name": "c.name",
        "released_at": "c.released_at",
    }
    order_col = order_map.get(f.order_by, "c.edhrec_rank")
    order_dir = "DESC" if str(f.order_dir).upper() == "DESC" else "ASC"

    join_fts = bool(f.text_query)

    where: List[str] = []
    params: List[Any] = []

    if join_fts:
        where.append("cards_fts MATCH ?")
        params.append(f.text_query)

    if f.name_contains:
        where.append("c.name LIKE ?")
        params.append(f"%{f.name_contains}%")

    if f.type_contains_any:
        clause, clause_params = _like_any("c.type_line", list(f.type_contains_any))
        where.append(clause)
        params.extend(clause_params)

    if f.oracle_contains:
        where.append("c.oracle_text LIKE ?")
        params.append(f"%{f.oracle_contains}%")

    if f.cmc_min is not None:
        where.append("c.cmc >= ?")
        params.append(f.cmc_min)

    if f.cmc_max is not None:
        where.append("c.cmc <= ?")
        params.append(f.cmc_max)

    if f.colors_any:
        cols = parse_colors(f.colors_any)
        if cols:
            clause, clause_params = _like_any("c.colors", cols)
            where.append(clause)
            params.extend(clause_params)

    if f.commander_ci is not None:
        allowed = parse_colors(f.commander_ci)
        clause, clause_params = _ci_subset_clause("c.color_identity", allowed)
        where.append(clause)
        params.extend(clause_params)

    if f.legal_format:
        col = _legal_col(f.legal_format)
        where.append(f"{col} = ?")
        params.append(f.legal_value)

    if f.rarity:
        where.append("c.rarity = ?")
        params.append(f.rarity)

    if f.set_code:
        where.append('c."set" = ?')
        params.append(f.set_code)

    if f.price_usd_max is not None:
        where.append("(c.price_usd IS NOT NULL AND c.price_usd <= ?)")
        params.append(f.price_usd_max)

    if f.keywords_any:
        clause, clause_params = _like_any("c.keywords", list(f.keywords_any))
        where.append(clause)
        params.extend(clause_params)

    if f.mechanic_tags_any:
        clause, clause_params = _like_any("c.mechanic_tags", list(f.mechanic_tags_any))
        where.append(clause)
        params.extend(clause_params)

    where_sql = " AND ".join(where) if where else "1=1"

    # Quote fields for safety, and qualify with table alias c.
    select_sql = ", ".join([f'c."{col}"' for col in fields])

    sql = f"""
    SELECT {select_sql}
    FROM cards c
    {"JOIN cards_fts ON cards_fts.rowid = c.rowid" if join_fts else ""}
    WHERE {where_sql}
    ORDER BY {order_col} {order_dir}
    LIMIT ? OFFSET ?;
    """

    params.extend([int(f.limit), int(f.offset)])

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
