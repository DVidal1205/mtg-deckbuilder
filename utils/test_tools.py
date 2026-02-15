#!/usr/bin/env python3
"""
test_tools.py — Exercise every tool the way an LLM would use them during a
deckbuilding session.

Runs each tool with representative arguments, prints the output, and reports
pass/fail status.  Uses only local DB tools by default.  Pass --edhrec to
also test the EDHREC tools (requires network).

Usage:
    python utils/test_tools.py              # local tools only
    python utils/test_tools.py --edhrec     # include EDHREC tools
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
DECKS = os.path.join(ROOT, "decks")
PYTHON = sys.executable

# Sample decklist for deck_stats testing (when no real decklists exist)
SAMPLE_DECKLIST = """\
# Krenko Goblins

| | |
|---|---|
| **Commander** | Krenko, Mob Boss |
| **Color Identity** | R |
| **Bracket** | 3 |

## Strategy

Go wide with goblins, overwhelm with tokens and tribal synergy. Krenko doubles the goblin count every activation — protect him, give him haste, and close games fast with Impact Tremors or Shared Animosity.

## Decklist

```
1 Krenko, Mob Boss
1 Skirk Prospector
1 Goblin Chirurgeon
1 Goblin Lackey
1 Goblin Recruiter
1 Goblin Warchief
1 Goblin Chieftain
1 Goblin Matron
1 Hobgoblin Bandit Lord
1 Battle Cry Goblin
1 Conspicuous Snoop
1 Foundry Street Denizen
1 Goblin Trashmaster
1 Siege-Gang Lieutenant
1 Purphoros, God of the Forge
1 Dockside Extortionist
1 Imperial Recruiter
1 Goblin Engineer
1 Bloodmark Mentor
1 Torch Courier
1 Goblin Piledriver
1 Mogg War Marshal
1 Rundvelt Hordemaster
1 Legion Warboss
1 Pashalik Mons
1 Muxus, Goblin Grandee
1 Deflecting Swat
1 Chaos Warp
1 Lightning Bolt
1 Tibalt's Trickery
1 Goblin War Strike
1 Massive Raid
1 Hordeling Outburst
1 Blasphemous Act
1 Wheel of Fortune
1 Impact Tremors
1 Shared Animosity
1 Mana Echoes
1 Goblin Bombardment
1 Sol Ring
1 Arcane Signet
1 Ruby Medallion
1 Lightning Greaves
1 Skullclamp
1 Thornbite Staff
1 Thousand-Year Elixir
1 Coat of Arms
1 Ashnod's Altar
1 Slate of Ancestry
1 Zariel, Archduke of Avernus
1 Command Tower
1 Ancient Tomb
1 Cavern of Souls
1 Castle Embereth
1 Hanweir Battlements
1 Buried Ruin
28 Mountain
1 Hidden Volcano
1 Amonkhet Raceway
1 Otawara, Soaring City
```
"""

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_tool(label: str, cmd: list[str], expect_success: bool = True) -> bool:
    """Run a tool command and print its output. Returns True if it passed."""
    full_cmd = [PYTHON] + cmd
    display_cmd = " ".join(cmd)

    print(f"\n{CYAN}{'─' * 70}{RESET}")
    print(f"{BOLD}{label}{RESET}")
    print(f"{YELLOW}$ python {display_cmd}{RESET}\n")

    start = time.time()
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True, text=True, timeout=30,
            cwd=ROOT,
        )
        elapsed = time.time() - start

        output = result.stdout.strip()
        if output:
            # Indent output for readability
            for line in output.split("\n"):
                print(f"  {line}")

        if result.stderr.strip():
            for line in result.stderr.strip().split("\n"):
                print(f"  {RED}stderr: {line}{RESET}")

        passed = (result.returncode == 0) == expect_success
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"\n  [{status}] exit={result.returncode}  ({elapsed:.2f}s)")
        return passed

    except subprocess.TimeoutExpired:
        print(f"  {RED}TIMEOUT (30s){RESET}")
        return False
    except Exception as e:
        print(f"  {RED}ERROR: {e}{RESET}")
        return False


def find_decklist() -> str | None:
    """Find a decklist to test with (.md preferred, .txt fallback)."""
    if os.path.isdir(DECKS):
        for ext in (".md", ".txt"):
            for f in sorted(os.listdir(DECKS)):
                if f.endswith(ext) and not f.startswith("_test"):
                    return os.path.join(DECKS, f)
    return None


def main():
    parser = argparse.ArgumentParser(description="Test all deckbuilding tools.")
    parser.add_argument("--edhrec", action="store_true",
                        help="Also test EDHREC tools (requires network)")
    args = parser.parse_args()

    results: list[tuple[str, bool]] = []

    print(f"\n{BOLD}{'=' * 70}")
    print(f"  MTG Commander Deckbuilder — Tool Test Suite")
    print(f"{'=' * 70}{RESET}\n")

    # ── card_lookup.py ────────────────────────────────────────────────────

    results.append(("card_lookup: exact match", run_tool(
        "card_lookup.py — Exact match (Sol Ring)",
        ["tools/card_lookup.py", "Sol Ring"],
    )))

    results.append(("card_lookup: partial match", run_tool(
        "card_lookup.py — Partial match ('Rhystic')",
        ["tools/card_lookup.py", "Rhystic"],
    )))

    results.append(("card_lookup: fuzzy/typo", run_tool(
        "card_lookup.py — Fuzzy match ('Dockside Extor')",
        ["tools/card_lookup.py", "Dockside Extor"],
    )))

    # ── card_search.py — structured search ────────────────────────────────

    results.append(("card_search: type+keyword+ci", run_tool(
        "card_search.py — Creatures with flying, CMC ≤ 3, Azorius identity",
        ["tools/card_search.py", "--type", "creature", "--keyword", "flying",
         "--cmc-max", "3", "--color-identity", "WU", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: is-commander", run_tool(
        "card_search.py — Simic commanders, sorted by EDHREC rank",
        ["tools/card_search.py", "--is-commander", "--color-identity", "GU",
         "--max", "10", "--sort", "edhrec_rank"],
    )))

    results.append(("card_search: colorless commanders", run_tool(
        "card_search.py — Colorless commanders",
        ["tools/card_search.py", "--is-commander", "--color-identity", "C", "--max", "5"],
    )))

    # ── card_search.py — discovery features ───────────────────────────────

    results.append(("card_search: multi-text OR", run_tool(
        "card_search.py — Multi-pattern text: death triggers (OR'd)",
        ["tools/card_search.py",
         "--text", "when a creature dies", "whenever a creature you control dies",
         "--color-identity", "BG", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: FTS5 phrase", run_tool(
        'card_search.py — FTS5 phrase: "sacrifice a creature"',
        ["tools/card_search.py", "--fts", '"sacrifice a creature"',
         "--color-identity", "BG", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: FTS5 NEAR", run_tool(
        "card_search.py — FTS5 NEAR: sacrifice + creature",
        ["tools/card_search.py", "--fts", "NEAR(sacrifice creature)",
         "--color-identity", "BG", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: --like discovery", run_tool(
        "card_search.py — Similar cards: --like 'Grave Pact'",
        ["tools/card_search.py", "--like", "Grave Pact",
         "--color-identity", "BG", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: --like discovery 2", run_tool(
        "card_search.py — Similar cards: --like 'Rhystic Study'",
        ["tools/card_search.py", "--like", "Rhystic Study",
         "--color-identity", "WU", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: multiple keywords OR", run_tool(
        "card_search.py — Multiple keywords: flying OR deathtouch",
        ["tools/card_search.py", "--keyword", "flying", "deathtouch",
         "--color-identity", "BG", "--cmc-max", "4", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: tag search", run_tool(
        "card_search.py — Mechanic tag: blink",
        ["tools/card_search.py", "--tag", "blink",
         "--color-identity", "WU", "--commander-legal", "--max", "10"],
    )))

    results.append(("card_search: verbose output", run_tool(
        "card_search.py — Verbose: show oracle text for ramp in green",
        ["tools/card_search.py", "--text", "search your library for a basic land",
         "--color-identity", "G", "--commander-legal", "--max", "5", "--verbose"],
    )))

    results.append(("card_search: name search", run_tool(
        "card_search.py — Name contains: 'Elesh'",
        ["tools/card_search.py", "--name", "Elesh", "--commander-legal", "--max", "10"],
    )))

    # ── color_identity.py ─────────────────────────────────────────────────

    results.append(("color_identity: commanders", run_tool(
        "color_identity.py — Golgari commanders",
        ["tools/color_identity.py", "BG", "--commanders-only", "--max", "10"],
    )))

    results.append(("color_identity: with text filter", run_tool(
        "color_identity.py — Boros cards with 'exile' in text",
        ["tools/color_identity.py", "RW", "--text", "exile",
         "--commander-legal", "--max", "10"],
    )))

    results.append(("color_identity: 5-color commanders", run_tool(
        "color_identity.py — Five-color commanders",
        ["tools/color_identity.py", "WUBRG", "--commanders-only", "--max", "10"],
    )))

    results.append(("color_identity: colorless", run_tool(
        "color_identity.py — Colorless commanders",
        ["tools/color_identity.py", "C", "--commanders-only", "--max", "5"],
    )))

    # ── deck_stats.py ─────────────────────────────────────────────────────

    decklist = find_decklist()
    if not decklist:
        # Create a small sample decklist for testing
        decklist = os.path.join(DECKS, "_test_sample.md")
        with open(decklist, "w") as f:
            f.write(SAMPLE_DECKLIST)
        created_sample = True
    else:
        created_sample = False

    results.append(("deck_stats: analyze decklist", run_tool(
        f"deck_stats.py — Analyze {os.path.basename(decklist)}",
        ["tools/deck_stats.py", decklist],
    )))

    # Clean up temp decklist
    if created_sample and os.path.exists(decklist):
        os.remove(decklist)

    # ── EDHREC tools (optional) ───────────────────────────────────────────

    if args.edhrec:
        results.append(("edhrec_commander: overview", run_tool(
            "edhrec_commander.py — Overview: Meren of Clan Nel Toth",
            ["tools/edhrec_commander.py", "Meren of Clan Nel Toth"],
        )))

        results.append(("edhrec_commander: high-synergy", run_tool(
            "edhrec_commander.py — High synergy: Korvold, Fae-Cursed King",
            ["tools/edhrec_commander.py", "Korvold, Fae-Cursed King",
             "--section", "high-synergy"],
        )))

        results.append(("edhrec_commander: combos", run_tool(
            "edhrec_commander.py — Combos: Meren of Clan Nel Toth",
            ["tools/edhrec_commander.py", "Meren of Clan Nel Toth",
             "--section", "combos"],
        )))

        results.append(("edhrec_commander: average-deck", run_tool(
            "edhrec_commander.py — Average deck: Krenko, Mob Boss",
            ["tools/edhrec_commander.py", "Krenko, Mob Boss",
             "--section", "average-deck"],
        )))

        results.append(("edhrec_top_cards: all types", run_tool(
            "edhrec_top_cards.py — All cards: Meren of Clan Nel Toth",
            ["tools/edhrec_top_cards.py", "Meren of Clan Nel Toth", "--max", "5"],
        )))

        results.append(("edhrec_top_cards: creatures", run_tool(
            "edhrec_top_cards.py — Creatures: Korvold, Fae-Cursed King",
            ["tools/edhrec_top_cards.py", "Korvold, Fae-Cursed King",
             "--type", "creatures", "--max", "10"],
        )))

        results.append(("edhrec_top_cards: high-synergy", run_tool(
            "edhrec_top_cards.py — High synergy: Krenko, Mob Boss",
            ["tools/edhrec_top_cards.py", "Krenko, Mob Boss",
             "--type", "high-synergy", "--max", "10"],
        )))

    # ── Summary ───────────────────────────────────────────────────────────

    print(f"\n{BOLD}{'=' * 70}")
    print(f"  Results Summary")
    print(f"{'=' * 70}{RESET}\n")

    passed = sum(1 for _, p in results if p)
    failed = sum(1 for _, p in results if not p)

    for name, p in results:
        status = f"{GREEN}PASS{RESET}" if p else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {name}")

    print(f"\n  {BOLD}{passed} passed, {failed} failed, {len(results)} total{RESET}")

    if failed:
        print(f"\n  {RED}Some tests failed!{RESET}")
        sys.exit(1)
    else:
        print(f"\n  {GREEN}All tests passed!{RESET}")


if __name__ == "__main__":
    main()
