# Mizzix — Spellslinger (final)

| | |
|---|---|
| **Commander** | Mizzix of the Izmagnus |
| **Color identity** | UR |
| **Mainboard** | 99 |
| **Last updated** | 2026-04-15 (mana base tuned) |
| **Moxfield ID** | pjT8Azi5O0ixSAI-23KvWw |
| **Moxfield Name** | Mizzix - Spells |

**Moxfield:** [Mizzix - Spells](https://www.moxfield.com/decks/pjT8Azi5O0ixSAI-23KvWw) · **Scryfall (commander):** [Mizzix of the Izmagnus](https://scryfall.com/card/cmm/348/mizzix-of-the-izmagnus)

## Game plan

1. **Cast Mizzix and climb experience** — Play instants and sorceries with **mana value greater than your experience count** so Mizzix keeps handing out counters; every counter makes future instants and sorceries **{1} cheaper** (generic reduction only).
2. **Stack discounts** — **Baral**, **Ral** (front), **Dirgur** (while prepared), **Mindsplice Apparatus**, and **Primal Amulet** all reduce spell costs and **compound** with Mizzix.
3. **Double triggers** — **[Harmonic Prodigy](https://scryfall.com/card/soc/123/harmonic-prodigy)** (*Secrets of Camelot*): *If a triggered ability of a Shaman or **another Wizard** you control triggers, that ability triggers an additional time.* **Mizzix** is a Wizard, so **experience triggers** and **Archmage Emeritus** magecraft (among others) can **fire twice** while Prodigy is out.
4. **Protect the commander** — **Fierce Guardianship**, **Deflecting Swat**, **Swiftfoot Boots**, **Riptide Laboratory**, **Command Beacon**, **Mistrise Village** (uncounterable line), and a **deep counter suite** keep Mizzix on the table.
5. **Close** — **X** burn (**Comet Storm**, **Crackle with Power**, **Bonfire**, **Jaya**), **Prismari** / **Storm King’s Thunder** / **Epic Experiment** chains, **Mizzix’s Mastery** overload, **Time Stretch**, and **Treasure** from **Storm-Kiln Artist** and **Hell to Pay**.

## Key packages

| Package | Cards |
|--------|--------|
| **Experience & triggers** | Mizzix, Katara, Harmonic Prodigy, Flux Channeler, Experimental Augury, Fuel for the Cause, Radstorm, Expansion Algorithm |
| **Draw & selection** | Rhystic Study, Mystic Remora, Frantic Search, Archmage Emeritus, Finale of Revelation, Drown in Dreams, Thassa’s Intervention, Mystic Confluence, Firemind’s Foresight, Wisdom of Ages |
| **Counters** | Fierce Guardianship, Mana Drain, Counterspell, Rewind, Spell Burst, Power Sink, Fuel for the Cause, Mystic Confluence, Thassa’s Intervention |
| **Removal & tempo** | Cyclonic Rift, Capsize, Swan Song, Blasphemous Act, Curse of the Swine, Hell to Pay, Aetherize, Otawara |
| **Copy & storm** | Storm King’s Thunder, Reiterate, Narset’s Reversal, Increasing Vengeance, Turnabout, Prismari, Radstorm, Epic Experiment |
| **Recursion** | Lier, Divergent Equation, Mystic Sanctuary, Mizzix’s Mastery, Wisdom of Ages |
| **Mana** | Sol Ring, Arcane Signet, Bender’s Waterskin, Resonating Lute, Treasures, **Resonating Lute** spell-only doubling |

## Mana base (optimized — utility unchanged)

**Constraint:** All **utility lands** stay as-is: Arcane Lighthouse, Command Beacon, Mystic Sanctuary, Otawara, Reliquary Tower, Riptide Laboratory, Mistrise Village.

**Pip check (mainboard + commander, `cards.json`):** about **64** blue and **30** red **colored mana symbols** in casting costs → roughly **68% blue / 32% red**. The old **10 Island / 5 Mountain** basics skewed **too red** versus that split (duals and fetches add **both** colors equally, so mono **Mountain**s were over-weighting red sources).

**Changes (still 36 lands):**

| Change | Why |
|--------|-----|
| **11 Island**, **3 Mountain** | Shift basics toward **blue** to track **~68% / ~32%** pip weight; still plenty of **duals + fetches + rocks** for early **RR** / **RRR** |
| **+Spirebluff Canal**, **−1 Mountain** (net vs old list: **+1 untapped UR dual**, **−2 Mountain**, **+1 Island**) | **Fast** Izzet land (untapped while you’re low on lands); replaces a **slow red-only** basic with a **blue + red** source, which **helps the U:R balance** more than another Mountain |

**Fixing package (non-utility):** Cascade Bluffs, Command Tower, Fiery Islet, Riverglide Pathway, Scorched Geyser, Shivan Reef, **Spirebluff Canal**, Steam Vents, Stormcarved Coast, Sulfur Falls, Training Center, Turbulent Springs, Volcanic Island, Prismatic Vista, Scalding Tarn.

## Decklist (99)

```
1 Mizzix of the Izmagnus
1 Aetherize
1 Arcane Lighthouse
1 Arcane Signet
1 Archmage Emeritus
1 Baral, Chief of Compliance
1 Bender's Waterskin
1 Blasphemous Act
1 Bonfire of the Damned
1 Capsize
1 Cascade Bluffs
1 Comet Storm
1 Command Beacon
1 Command Tower
1 Counterspell
1 Crackle with Power
1 Curse of the Swine
1 Cyclonic Rift
1 Deflecting Swat
1 Dirgur Focusmage
1 Divergent Equation
1 Drown in Dreams
1 Electrodominance
1 Epic Experiment
1 Expansion Algorithm
1 Experimental Augury
1 Fierce Guardianship
1 Fiery Islet
1 Finale of Revelation
1 Firemind's Foresight
1 Flux Channeler
1 Frantic Search
1 Fuel for the Cause
1 Harmonic Prodigy
1 Hell to Pay
1 Increasing Vengeance
11 Island
1 Jaya's Immolating Inferno
1 Katara, Waterbending Master
1 Lier, Disciple of the Drowned
1 Mana Drain
1 Mindsplice Apparatus
1 Mistrise Village
1 Mizzix's Mastery
3 Mountain
1 Mystic Confluence
1 Mystic Remora
1 Mystic Sanctuary
1 Mystic Speculation
1 Narset's Reversal
1 Otawara, Soaring City
1 Power Sink
1 Primal Amulet
1 Prismari, the Inspiration
1 Prismatic Vista
1 Propaganda
1 Radstorm
1 Ral, Monsoon Mage
1 Reiterate
1 Reliquary Tower
1 Resonating Lute
1 Rewind
1 Rhystic Study
1 Riptide Laboratory
1 Riverglide Pathway
1 Scalding Tarn
1 Scorched Geyser
1 Shivan Reef
1 Sol Ring
1 Spell Burst
1 Spirebluff Canal
1 Steam Vents
1 Storm King's Thunder
1 Storm-Kiln Artist
1 Stormcarved Coast
1 Sulfur Falls
1 Swan Song
1 Swiftfoot Boots
1 Talrand, Sky Summoner
1 Thassa's Intervention
1 Time Stretch
1 Training Center
1 Turbulent Springs
1 Turnabout
1 Veyran, Voice of Duality
1 Vivi Ornitier
1 Volcanic Island
1 Wisdom of Ages
```

### Type breakdown (Scryfall types, first face)

| Type | Count |
|------|------:|
| Land | 36 |
| Instant | 27 |
| Creature | 13 |
| Sorcery | 13 |
| Artifact | 7 |
| Enchantment | 3 |

*Type totals from Scryfall first face; automated tools that treat `Primal Amulet // Primal Wellspring` as a land type line will over-count lands by one.*
