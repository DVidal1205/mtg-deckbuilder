# Deckbuilding Process

Follow this staged process for new deck requests. Compress or skip stages if the user comes in with a clear vision.

## Stage 1: Discovery
Ask about (only what's unclear — don't interrogate):
- **Commander**: Who's at the helm? Or are they looking for commander recommendations?
- **Strategy / Theme**: What's the deck trying to do? Combo? Value? Aggro? Theme/flavor? Specific mechanic?
- **Target bracket**: What bracket are they building for? (see 04-brackets.md)
- **Playgroup context**: Anything about their meta? Fast combo? Battlecruiser? Stax-friendly?
- **Cards they want to include**: Pet cards, recent pulls, specific combos they want to run
- **Cards or strategies they want to AVOID**: Things they find unfun or don't want to play against

Do NOT ask about budget. It is never relevant.

## Stage 2: Skeleton
Before filling out 100 cards, define the deck's architecture:
- **Commander role**: Is the commander the engine, the payoff, the enabler, or just color access?
- **Win condition(s)**: Primary and backup. How does this deck actually close games?
- **Slot allocation** (rough targets, adjusted per strategy):
  - Ramp: 10-14
  - Card draw / advantage: 10-12
  - Removal (targeted): 5-8
  - Board wipes: 2-4
  - Threats / Win cons: 8-15
  - Synergy / Engine pieces: 15-25
  - Utility / Protection / Recursion: 5-10
  - Lands: 35-38
- **Key synergies**: What's the engine? What makes this deck tick beyond generic goodstuff?
- **Curve target**: What average mana value are we shooting for?

Present this skeleton to the user and get buy-in before filling slots.

## Stage 3: Card Selection
- Query the local database for candidates in each slot, filtered by color identity and commander legality
- Check EDHREC for the commander to see popular inclusions and find cards you might miss
- Present options with brief reasoning for key slots (don't enumerate every card — focus on interesting choices and tradeoffs)
- Fill out the full 100-card list
- Save to `decks/`

## Stage 4: Mana Base
- Count colored pips across all nonland cards to determine color weight
- Select lands that support the color needs AND the deck's speed:
  - Fast mana (Mana Crypt, Sol Ring, Mana Vault, etc.)
  - Fetch lands + dual lands (original duals, shocks, etc.) for 2+ color decks
  - Utility lands that support the strategy (e.g., Urborg for black, Gaea's Cradle for creature decks, etc.)
  - Consider how many basics are needed for basic-land-fetching effects
- Reminder: budget doesn't matter. Always use the best lands available

## Stage 5: Refinement
- Review the final list against the skeleton — are all roles filled?
- Check the mana curve — is it appropriate for the strategy and bracket?
- Look for dead draws — cards that are bad in multiples (singleton helps, but watch for too many narrow cards)
- Check for missing interaction — can this deck answer common threats?
- Identify flex slots — cards that are the weakest links and could be swapped
- Verify bracket appropriateness (see 04-brackets.md)

## Iteration
When the user wants to modify an existing deck:
- Read the current decklist from `decks/`
- **Run `fetch_full_deck` on the deck file** so you have every card's mana cost and oracle text in context when proposing swaps, adds, or cuts
- Understand the REASON for the change (meta shift, underperforming cards, new printings, power level adjustment, more fun)
- **At 100 cards:** Never cut without asking first. Propose 3–5 cut options with brief rationale and let the user choose. (Adding a card forces a cut; present alternatives.)
- **Under 100 cards:** Suggest adds and cuts freely to fill out the list.
- Propose specific swaps with reasoning
- Update and re-save the file
- Run deck_stats.py to verify the changes didn't break the deck's structure
