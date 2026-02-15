# Commander Format Rules Reference

## Core Rules
- **Deck size**: Exactly 100 cards, including the commander(s)
- **Singleton**: Only one copy of each card, EXCEPT basic lands (Plains, Island, Swamp, Mountain, Forest, Wastes)
- **Color identity**: Every card in the deck must fall within the commander's color identity
  - Color identity = the card's colors + any mana symbols appearing in its rules text or mana cost
  - Lands with colored mana abilities HAVE that color identity (e.g., Blood Crypt is R/B)
  - Reminder text and flavor text do NOT affect color identity
  - Hybrid mana symbols count as BOTH colors
  - Phyrexian mana symbols count as their color
  - Extort's reminder text ({W/B}) does NOT count
- **Commander**: Must be a legendary creature (or a card that says it can be your commander, e.g., certain planeswalkers)
- **Partner**: Some commanders have Partner, allowing two commanders. Color identity is the combined identity of both. The deck is still exactly 100 cards total including both commanders
- **Partner with**: Some commanders can only partner with a specific other commander
- **Friends forever**, **Choose a Background**, **Doctor's companion**: Other pairing mechanics that function like Partner but with restrictions
- **Starting life**: 40 per player
- **Commander damage**: 21 combat damage from a single commander = that player loses (tracked separately per commander)
- **Command zone**: Commander starts in the command zone. Can be cast from there. Each subsequent cast costs {2} more (commander tax)
- **Zone changes**: When a commander would go to the graveyard or exile from anywhere, its owner may put it back in the command zone instead
- **Multiplayer default**: Free-for-all, 4 players. Last player standing wins

## Ban List
The Commander ban list is maintained by the Commander Rules Committee. **Always verify legality using the local database** (`legalities->>'commander' = 'legal'`). Do not rely on memory — the ban list changes.

**The local database is the source of truth.** Never doubt the DB: if it says a card is banned, the card is banned. Do not suggest the DB might be wrong or that a card is "actually legal" elsewhere.

Some high-profile cards to be aware of are banned (like Primeval Titan, Sundering Titan, Biorhythm, Mana Crypt, etc.) but always verify in the DB rather than assuming.

## Companion
Companions work in Commander with special rules:
- The companion must meet its restriction using your entire 100-card deck (including commander)
- The companion is NOT part of your 100 — it's a 101st card in your sideboard/companion zone
- The companion ability costs {3} to move to hand (as of the companion errata)
