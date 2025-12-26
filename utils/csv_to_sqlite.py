#!/usr/bin/env python3
"""
Import Scryfall-flattened MTG cards CSV into SQLite with helpful indexes and optional FTS5.

Usage:
  python3 utils/csv_to_sqlite.py /path/to/cards.csv /path/to/cards.db

Notes:
- Designed for local dev + agent tool calls.
- Stores most columns as TEXT for robustness; key numeric fields are cast.
- Creates indexes for common deckbuilding queries.
- Creates FTS5 virtual table for fast text search over rules text.
"""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple

# --- Columns that should be numeric (best-effort cast) ---
INT_COLS = {
    "cmc",
    "color_count",
    "color_identity_count",
    "keyword_count",
    "produced_mana_count",
    "all_parts_count",
    "mechanic_tag_count",
    "card_faces_count",
    "attraction_lights_count",
    "edhrec_rank",
    "penny_rank",
    "mtgo_id",
    "mtgo_foil_id",
    "tcgplayer_id",
    "tcgplayer_etched_id",
    "cardmarket_id",
    "multiverse_id",
    "arena_id",
    "resource_id",
}

REAL_COLS = {
    "price_usd",
    "price_usd_foil",
    "price_usd_etched",
    "price_eur",
    "price_eur_foil",
    "price_eur_etched",
    "price_tix",
}

BOOLISH_COLS = {
    # many of these are "True/False" strings in your CSV
    "highres_image",
    "digital",
    "full_art",
    "textless",
    "booster",
    "story_spotlight",
    "game_changer",
    "foil",
    "nonfoil",
    "oversized",
    "promo",
    "reprint",
    "variation",
    "reserved",
    "content_warning",
}


# --- Legalities columns (string like "legal", "not_legal", etc.) ---
LEGALITY_PREFIX = "legal_"


def cast_value(col: str, val: str):
    """Best-effort casting based on column name."""
    if val is None:
        return None
    v = val.strip()
    if v == "":
        return None

    if col in BOOLISH_COLS:
        # accept "True/False", "true/false", "1/0", "yes/no"
        low = v.lower()
        if low in ("true", "1", "yes", "y", "t"):
            return 1
        if low in ("false", "0", "no", "n", "f"):
            return 0
        # fall back to TEXT if weird
        return v

    if col in INT_COLS:
        try:
            return int(float(v))  # sometimes arrives as "3.0"
        except ValueError:
            return v

    if col in REAL_COLS:
        try:
            return float(v)
        except ValueError:
            return v

    # keep legalities as TEXT (legal / not_legal / restricted / banned)
    if col.startswith(LEGALITY_PREFIX):
        return v

    return v


def sqlite_type_for(col: str) -> str:
    """Choose SQLite type affinity."""
    if col in INT_COLS or col in BOOLISH_COLS:
        return "INTEGER"
    if col in REAL_COLS:
        return "REAL"
    return "TEXT"


def create_schema(conn: sqlite3.Connection, columns: List[str], use_fts: bool = True) -> None:
    cur = conn.cursor()

    col_defs = []
    for c in columns:
        if c == "id":
            col_defs.append(f'"{c}" TEXT PRIMARY KEY')
        else:
            col_defs.append(f'"{c}" {sqlite_type_for(c)}')

    cur.execute("DROP TABLE IF EXISTS cards")
    cur.execute(f"CREATE TABLE cards ({', '.join(col_defs)})")

    # Helpful indexes (tune as needed)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_cmc ON cards(cmc)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_type_line ON cards(type_line)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_color_identity ON cards(color_identity)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_legal_commander ON cards(legal_commander)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_price_usd ON cards(price_usd)")
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cards_set ON cards("set")')

    # Optional: FTS5 for fast searching name/type/oracle text
    if use_fts:
        # Requires SQLite built with FTS5 (most modern distros are).
        cur.execute("DROP TABLE IF EXISTS cards_fts")
        cur.execute(
            """
            CREATE VIRTUAL TABLE cards_fts USING fts5(
              id UNINDEXED,
              name,
              type_line,
              oracle_text,
              face_oracle_texts,
              content='cards',
              content_rowid='rowid'
            )
            """
        )

        # Triggers to keep FTS in sync
        cur.execute("DROP TRIGGER IF EXISTS cards_ai")
        cur.execute("DROP TRIGGER IF EXISTS cards_ad")
        cur.execute("DROP TRIGGER IF EXISTS cards_au")

        cur.execute(
            """
            CREATE TRIGGER cards_ai AFTER INSERT ON cards BEGIN
              INSERT INTO cards_fts(rowid, id, name, type_line, oracle_text, face_oracle_texts)
              VALUES (new.rowid, new.id, new.name, new.type_line, new.oracle_text, new.face_oracle_texts);
            END;
            """
        )
        cur.execute(
            """
            CREATE TRIGGER cards_ad AFTER DELETE ON cards BEGIN
              INSERT INTO cards_fts(cards_fts, rowid, id, name, type_line, oracle_text, face_oracle_texts)
              VALUES ('delete', old.rowid, old.id, old.name, old.type_line, old.oracle_text, old.face_oracle_texts);
            END;
            """
        )
        cur.execute(
            """
            CREATE TRIGGER cards_au AFTER UPDATE ON cards BEGIN
              INSERT INTO cards_fts(cards_fts, rowid, id, name, type_line, oracle_text, face_oracle_texts)
              VALUES ('delete', old.rowid, old.id, old.name, old.type_line, old.oracle_text, old.face_oracle_texts);
              INSERT INTO cards_fts(rowid, id, name, type_line, oracle_text, face_oracle_texts)
              VALUES (new.rowid, new.id, new.name, new.type_line, new.oracle_text, new.face_oracle_texts);
            END;
            """
        )

    conn.commit()


def insert_rows(
    conn: sqlite3.Connection,
    columns: List[str],
    rows: List[Dict[str, str]],
) -> None:
    cur = conn.cursor()
    placeholders = ", ".join(["?"] * len(columns))
    col_sql = ", ".join([f'"{c}"' for c in columns])
    sql = f"INSERT INTO cards ({col_sql}) VALUES ({placeholders})"

    values: List[Tuple] = []
    for r in rows:
        values.append(tuple(cast_value(c, r.get(c, "")) for c in columns))

    cur.executemany(sql, values)


def import_csv(csv_path: str, db_path: str, use_fts: bool = True, batch_size: int = 2000) -> None:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-200000;")  # ~200MB cache if available

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no headers")

        columns = [h.strip() for h in reader.fieldnames]
        create_schema(conn, columns, use_fts=use_fts)

        batch: List[Dict[str, str]] = []
        total = 0

        conn.execute("BEGIN")
        for row in reader:
            batch.append(row)
            if len(batch) >= batch_size:
                insert_rows(conn, columns, batch)
                total += len(batch)
                batch.clear()
                if total % 10000 == 0:
                    print(f"Imported {total} rows...")

        if batch:
            insert_rows(conn, columns, batch)
            total += len(batch)
            batch.clear()

        conn.commit()

    # Analyze for query planner (nice boost)
    conn.execute("ANALYZE;")
    conn.commit()
    conn.close()

    print(f"Done. Imported {total} rows into {db_path}")
    if use_fts:
        print("FTS5 enabled: cards_fts (search name/type/oracle/face_oracle_texts)")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 utils/csv_to_sqlite.py data/cards.csv data/cards.db")
        sys.exit(1)

    csv_path = sys.argv[1]
    db_path = sys.argv[2]
    use_fts = True
    if len(sys.argv) >= 4:
        use_fts = sys.argv[3].lower() in ("1", "true", "yes", "y")

    import_csv(csv_path, db_path, use_fts=use_fts)


if __name__ == "__main__":
    main()
