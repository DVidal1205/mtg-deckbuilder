from pathlib import Path
from pprint import pprint

from search_cards import CardSearchFilters, search_cards

DB = str(Path(__file__).resolve().parents[1] / "data" / "cards.db")


def show(title, rows, n=5):
    print("\n" + "=" * 90)
    print(title)
    print(f"Rows: {len(rows)} (showing up to {n})")
    for r in rows[:n]:
        # keep output readable
        print(f"- {r.get('name')} | {r.get('mana_cost')} | CI={r.get('color_identity')} | CMC={r.get('cmc')} | ${r.get('price_usd')}")


def main():
    # 1) FTS phrase search
    rows = search_cards(
        DB,
        CardSearchFilters(
            text_query='"take an extra turn"',
            legal_format="commander",
            limit=10,
            order_by="name",
        ),
    )
    show('FTS phrase: "take an extra turn" (commander legal)', rows)

    # 2) Blink-ish FTS (templating-based)
    rows = search_cards(
        DB,
        CardSearchFilters(
            text_query="exile NEAR return NEAR battlefield",
            legal_format="commander",
            commander_ci="UW",
            limit=25,
            order_by="edhrec_rank",
        ),
    )
    show("FTS: exile NEAR return NEAR battlefield | CI<=UW | commander legal", rows, n=10)

    # 3) Name substring filter (no FTS)
    rows = search_cards(
        DB,
        CardSearchFilters(
            name_contains="Sol Ring",
            legal_format="commander",
            limit=5,
            order_by="released_at",
        ),
    )
    show("Name contains: Sol Ring | commander legal", rows)

    # 4) Type + CMC + CI subset
    rows = search_cards(
        DB,
        CardSearchFilters(
            type_contains_any=["Creature"],
            cmc_max=2,
            commander_ci="U",
            legal_format="commander",
            limit=25,
            order_by="cmc",
        ),
    )
    show("Creatures CMC<=2 | CI<=U | commander legal", rows, n=10)

    # 5) Keywords filter (Scryfall keywords column, comma-separated)
    rows = search_cards(
        DB,
        CardSearchFilters(
            keywords_any=["Flying", "Ward"],
            legal_format="commander",
            commander_ci="UB",
            limit=25,
            order_by="edhrec_rank",
        ),
    )
    show("Keywords any of: Flying OR Ward | CI<=UB | commander legal", rows, n=10)

    # 6) Mechanic tags filter (your custom mechanic_tags column)
    # NOTE: This will only return meaningful results if you've populated mechanic_tags.
    rows = search_cards(
        DB,
        CardSearchFilters(
            mechanic_tags_any=["blink"],
            legal_format="commander",
            commander_ci="UW",
            limit=25,
            order_by="edhrec_rank",
        ),
    )
    show("Mechanic tag: blink | CI<=UW | commander legal", rows, n=10)

    # 7) Price filter sanity
    rows = search_cards(
        DB,
        CardSearchFilters(
            text_query='"draw a card"',
            legal_format="commander",
            commander_ci="G",
            price_usd_max=1.00,
            limit=25,
            order_by="price_usd",
        ),
    )
    show('FTS: "draw a card" | CI<=G | commander legal | price<=1.00', rows, n=10)

    # 8) CI subset enforcement sanity checks
    # If commander_ci="U", then a card with CI "U,R" must NOT appear.
    rows = search_cards(
        DB,
        CardSearchFilters(
            name_contains="Expressive Iteration",  # known UR card if present in your DB
            commander_ci="U",
            legal_format="commander",
            limit=10,
        ),
    )
    show("CI enforcement: Expressive Iteration searched under CI<=U (should be empty)", rows)

    # 9) Colorless is allowed under any CI (and under empty CI only colorless)
    rows = search_cards(
        DB,
        CardSearchFilters(
            name_contains="Sol Ring",
            commander_ci="U",
            legal_format="commander",
            limit=5,
        ),
    )
    show("Colorless allowed: Sol Ring under CI<=U", rows)

    rows = search_cards(
        DB,
        CardSearchFilters(
            text_query="sol ring",
            commander_ci="",  # only colorless should pass
            legal_format="commander",
            limit=10,
        ),
    )
    show("CI empty means only colorless allowed (should still find Sol Ring via FTS)", rows)


if __name__ == "__main__":
    main()
