# Mana Base Construction

Use this when building or evaluating land bases. Run `tools/deck_stats.py` on the deck first to get **mana source counts** (lands + rocks that produce each color); balance source counts and basics to support your spells' color needs.

## Land Count Baseline

| Avg Mana Value | Lands | Notes |
|----------------|-------|--------|
| &lt; 2.5 (cEDH) | 28–32 | Heavy fast mana compensates |
| 2.5–3.0 | 33–35 | Low curve, want to stop hitting lands early |
| 3.0–3.5 | 35–37 | The default for most decks |
| 3.5–4.0 | 37–38 | Need consistent land drops through turn 6+ |
| Lands-matter | 38–42 | Lands ARE the strategy |

**Adjust:** +1 land per color beyond 2. −1 per ~3 ramp pieces above baseline 10. MDFCs count as half a land.

## Pip Analysis (Do This First)

Before selecting lands, count every colored mana symbol across all **nonland** cards. This determines your color weight.

- If a Sultai deck has 45% black pips, 33% green, 22% blue — the colored sources should **roughly mirror that**. Don't default to even splits.
- **Minimum source targets:**
  - Single-pip cards you need on curve: **~15 sources** of that color
  - Double-pip costs ({B}{B}): **~20 sources** — be cautious with these in 3+ color decks
  - Splash colors (few cards): **10–12 sources** is fine

A **source** = any land or mana rock that produces that color. Count both.

## Land Categories

- **Dual lands (untapped, two colors):** Original duals, shock lands, pain lands, bond/battlebond lands. Core fixing — enter untapped, produce two colors. Prioritize these. Tradeoffs: life payment, conditions for untapped; pick by speed and bracket.
- **Fetch lands:** Search for a land. Find duals/shocks (any color those can produce), thin deck, trigger landfall/shuffle. In 3+ colors, off-color fetches still have value if they find a dual in your colors.
- **Tri-lands:** Produce three colors. Triomes/tricycle are fetchable; most ETB tapped — acceptable in slower decks, a cost in fast ones.
- **Rainbow lands:** Any color. Critical in 4–5 color; good in 3-color. Some have life costs or conditions.
- **Utility lands:** Do something beyond mana — removal, recursion, draw, gy hate, protection. Each one that doesn't produce colored mana is a **missing colored source**. Only include if they support the strategy or cover a critical function.
- **Basics:** Fetchable by most ramp, immune to nonbasic hate, required by "search for basic" effects. Weight by pip distribution. Rough counts: mono 25–30, two-color 10–18, three-color 5–10, four-color 3–6, five-color 2–5.

## Bracket Considerations

- **Bracket 1–2:** ETB tapped acceptable. Simpler fixing (basics, check lands). No need for full fetch/dual optimization.
- **Bracket 3:** Optimized fixing. Minimize ETB tapped (ideally 0–2 outside fetchable tri-lands). All relevant utility lands for the strategy.
- **Bracket 4 (cEDH):** Every land must produce mana immediately. Zero taplands. Maximum rainbow + fast mana. Efficiency above everything.

## Validation

After building the mana base, check:

- Colored source counts match pip distribution
- Enough basics for basic-fetching ramp in the deck
- Enough fetchable targets so fetches aren't dead late
- Utility lands aren't cannibalizing colored source needs
- ETB tapped count appropriate for bracket
- All lands within commander's color identity

## Common Traps

- **Too many colorless utility lands** — every one is a missing colored source
- **Ignoring pip weight** — match sources to actual pip distribution, not an even split
- **Unnecessary "value" lands** — don't include conditional draw or "no max hand size" lands unless the deck specifically needs them
- **ETB tapped at high power** — being a turn behind compounds in optimized pods
- **Not enough basics with basic-heavy ramp** — if the deck runs land-search ramp, it needs basics to find
- **Too many pay-life lands** — fetches + pain + shock + Mana Confluence add up; in mid-power (B3) you can easily burn 5–15 life per game. Prefer duals/bond/pain sparingly; use life payment only where speed is critical.
