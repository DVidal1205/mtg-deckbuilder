# Commander Deckbuilding Heuristics

These are starting points and rules of thumb. Deviate when the strategy demands it, but note when you're deviating and why.

## The Core Numbers (Baseline for a "Normal" Commander Deck)

These are starting allocations. Adjust based on strategy, commander, and bracket.

| Category | Slots | Notes |
|----------|-------|-------|
| Lands | 35-38 | 33-34 for very low curves or heavy ramp. 38-40 for landfall or high-curve |
| Ramp | 10-14 | Mix of rocks, dorks, and land ramp depending on colors and speed |
| Card Draw | 10-12 | Absolute minimum. Card draw wins Commander games |
| Targeted Removal | 5-8 | Must be able to answer artifacts, enchantments, and creatures at minimum |
| Board Wipes | 2-4 | Scales up for control, down for aggro/go-wide |
| Standalone Threats / Win Cons | 8-15 | Things that win the game or generate massive advantage on their own |
| Synergy / Engine | 15-25 | Deck-specific. The cards that make YOUR deck do its thing |
| Utility / Protection / Recursion | 5-10 | Counterspells, graveyard recursion, commander protection, etc. |

These overlap. A card can be "card draw" AND "synergy." Count it in whichever role it primarily fills, but be aware of how many roles each card serves — high "role density" per card is a hallmark of great deckbuilding.

## Mana Base Construction (see 07-mana-base.md)

### Ramp Priorities
- **Sol Ring** goes in every deck. Period
- For 2+ CMC commanders: fast mana matters more. You want to cast your commander ahead of curve
- Land-based ramp (Cultivate, Kodama's Reach, Nature's Lore, Three Visits) is more resilient than artifact ramp in metas with artifact removal
- Mana dorks are best in decks that want creatures or have low curves
- Artifact ramp (signets, talismans) is best in non-green decks or decks that want a fast, explosive start

### The Pip Rule
- For each colored pip in your deck, you need adequate sources. Rough guide:
  - If 30% of your colored pips are blue, ~30% of your colored sources should produce blue
  - Double-pip cards (like {W}{W} or {B}{B}) are harder in 3+ color decks. Be aware of this when including them

## Card Advantage

- **Card draw is THE most important category in Commander.** Games go long, you need gas
- Card draw that synergizes with your strategy is better than generic draw (e.g., Skullclamp in creature decks, Rhystic Study in decks that want to sit back, Sylvan Library in decks that care about top-of-deck)
- Wheel effects (Wheel of Fortune, Windfall) are powerful but help opponents too — use them deliberately, not as generic draw
- Engines > One-shots. Phyrexian Arena every turn > Harmonize once. But don't neglect one-shots entirely — sometimes you need draw NOW
- Tutors are a form of card advantage/selection. In higher brackets, include more. In lower brackets, lean on raw card draw for variance and fun

## Interaction & Removal

- **You MUST be able to interact.** A Commander deck that can't remove a problem permanent is not a real deck
- Minimum baseline: ways to deal with creatures, artifacts, enchantments, and (if in blue) stack-based threats
- Flexible removal is king: Beast Within, Generous Gift, Anguished Unmaking, Chaos Warp — cards that hit multiple types
- Spot removal vs. board wipes: you need both. Spot removal handles early threats; board wipes reset when you're behind
- Graveyard hate is increasingly mandatory. At least 1-2 pieces (Bojuka Bog, Soul-Guide Lantern, Dauthi Voidwalker, etc.)
- Don't overload on removal in synergy-heavy decks — you still need to execute your own gameplan

## Win Conditions

- **Every deck needs a clear plan to win.** "Attack with creatures" is fine IF the creatures are threatening enough to close a 120-life-total game
- Have a primary win con and at least one backup
- Infinite combos: appropriate at bracket 3+ and expected at bracket 4. At bracket 1-2, avoid or limit them
- Combat damage wins: need significant force multipliers in multiplayer (extra combats, Craterhoof, Triumph of the Hordes, etc.) to close out against 3 opponents
- Alternate win cons: if your deck can assemble one naturally, great. Don't force them
- Commander damage (21 from a single commander) is a viable win con for Voltron strategies

## Singleton Considerations

- Redundancy through effect density, not card copies. You can't play 4 Swords to Plowshares, but you CAN play StP + Path to Exile + Prismatic Ending + Solitude
- Tutors provide virtual redundancy. The more critical a combo piece, the more tutors you should run to find it
- Don't include too many narrow/situational cards. In singleton, you can't guarantee you'll draw them when needed
- Cards that are individually powerful AND synergistic with your deck are the best includes

## Commander-Specific Building

- **Build around, don't depend on.** The deck should function if the commander gets removed or taxed out of reach
- If the commander costs 4+, plan for only casting it 2-3 times per game. Each removal adds 2 to the cost
- If the deck IS very commander-dependent, run protection: Lightning Greaves, Swiftfoot Boots, Whispersilk Cloak, Tyvar's Stand, counterspells
- Consider your commander's role:
  - **Engine commanders** (e.g., Meren, Korvold): The deck feeds them, they generate value. Build around the engine loop
  - **Payoff commanders** (e.g., Purphoros, Teysa Karlov): The deck creates the conditions, the commander rewards you. Focus on generating triggers
  - **Enabler commanders** (e.g., Scion of the Ur-Dragon, Sisay): They find or cheat in your best cards. Focus on having great targets
  - **Value commanders** (e.g., Atraxa, Chulane): They provide incremental advantage. Build a strong standalone deck that gets better with the commander out
  - **Color access commanders** (e.g., Kenrith, Golos — when legal): You're mostly here for the colors. Build goodstuff or a theme the colors enable

## Multiplayer Dynamics

- Efficient 1-for-1 removal is worse in multiplayer than in 1v1. You spend a card to deal with one opponent's threat but the other two opponents are unaffected. Prioritize removal that's efficient enough to not feel bad or that doubles as value
- Board wipes hit all opponents — they're inherently better in multiplayer
- "Pillow fort" and deterrent cards scale well with more opponents
- Threat assessment matters: don't include cards that paint a target on your back unless you can defend that position or close the game quickly
- Political cards (Smothering Tithe, Rhystic Study, Trouble in Pairs) are extremely strong because they scale with number of opponents
