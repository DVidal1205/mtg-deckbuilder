# Output Formats

## Decklist Format

Save decklists to `decks/` as `.md` files. Filename: `{commander-slug}.md` (e.g., `meren-of-clan-nel-toth.md`).

The file has three parts:
1. **Metadata** — Markdown with deck info, strategy notes, and any context
2. **Decklist** — A **type breakdown table** (see below) followed by a fenced code block containing the raw, import-ready list (no comments, no section headers — just `N Card Name` lines that paste directly into Moxfield/Archidekt/etc.)
3. When saving or updating a deck, **include a type breakdown table** directly under the `## Decklist` header and above the code block. The table lists card type counts so the deck composition is visible at a glance. Use the format:

| Type | Count |
|------|-------|
| Creature | N |
| Instant | N |
| Sorcery | N |
| Enchantment | N |
| Artifact | N |
| Planeswalker | N |
| Land | N |

Only include rows for types that appear in the deck. Counts should sum to 100 (including commander). You can derive these from the decklist or from running `deck_stats.py` on the file.

```markdown
# Meren Reanimator

| | |
|---|---|
| **Commander** | Meren of Clan Nel Toth |
| **Color Identity** | BG |
| **Bracket** | 3 |
| **Date** | 2026-02-14 |

## Strategy

Sacrifice creatures for value, recur them with Meren's experience counters. Primary win through Gray Merchant loops and Kokusho drains. Backup win via Protean Hulk lines.

## Key Synergies

- Meren + Spore Frog = repeatable fog every turn
- Protean Hulk → Mikaeus + Walking Ballista = instant win
- Skullclamp + token generators = draw engine

## Notes

- Flex slots: Golgari Findbroker, Cavalier of Night
- Runs light on board wipes because we want our own creatures to stick
- Heavy on 2-3 CMC creatures to maximize early experience counters

## Decklist

| Type | Count |
|------|-------|
| Creature | 4 |
| Instant | 8 |
| Sorcery | 10 |
| Enchantment | 2 |
| Artifact | 5 |
| Land | 37 |

```
1 Meren of Clan Nel Toth
1 Sakura-Tribe Elder
1 Viscera Seer
1 Blood Artist
1 Skullclamp
1 Sol Ring
1 Ashnod's Altar
1 Grave Pact
1 Command Tower
15 Swamp
12 Forest
```
```

### Formatting Rules

- The **metadata section** is free-form markdown. Include whatever context is useful: strategy summary, key synergies, flex slots, meta considerations, playtest notes, etc.
- The **decklist code block** must be clean and import-ready:
  - Every line is `N Card Name` (e.g., `1 Sol Ring`, `15 Swamp`)
  - No comments, no section headers, no blank lines inside the block
  - No `//` prefixes — these break import tools
  - Sort order: commander first, then creatures, instants, sorceries, enchantments, artifacts, planeswalkers, lands (sorted by mana value ascending, then alphabetically within each group)
  - Basic lands can have counts > 1
- The LLM should be able to reconstruct category groupings from the database — they don't need to be in the file itself

## Playtest Notes Format

Save to `notes/` as `{commander-slug}-notes.md`:

```markdown
# [Deck Name] — Playtest Notes

## [Date] — [Session Type: Online/LGS/Casual Night]
**Pod**: [What decks were in the pod, if known]
**Result**: [Win/Loss, what turn, how]
**Observations**:
- What worked well
- What underperformed
- Cards that were dead in hand
- Cards that overperformed
- Matchup-specific notes
- Changes to consider

## [Date] — ...
```
