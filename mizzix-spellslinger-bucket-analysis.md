# Mizzix of the Izmagnus — Spellslinger reference

**Status:** Final **99**-card mainboard (2026-04-15). Canonical list and strategy: **`decks/mizzix-spells.md`**.

This file keeps a **bucket view** of the deck (roles for tuning and side discussions). Mana costs and types match **`data/cards.json`** (Scryfall bulk). Heuristics align with **`.cursor/rules/02-deckbuilding-heuristics.md`**.

---

## Harmonic Prodigy (rules note)

The **Secrets of Camelot** printing has **prowess** and:

> *If a triggered ability of a Shaman or **another Wizard** you control triggers, that ability triggers an additional time.*

**Mizzix of the Izmagnus** is a **Wizard**. While **Harmonic Prodigy** is on the battlefield, **Mizzix’s “whenever you cast an instant or sorcery…” experience trigger** is a **triggered ability of a Wizard you control** other than Prodigy — it **can resolve an additional time**. The same applies to other **Wizard** triggers you control (**Archmage Emeritus** magecraft, **Talrand** Drakes, **Baral**’s loot-when-you-counter, etc.) and to **Shaman** triggers (**Storm-Kiln Artist** Treasures). **Katara** is not a Wizard, so her abilities are unaffected by this line of text.

*(Older printings used different wording; always use the oracle text on your physical card.)*

---

## Bucket legend

| Bucket | Meaning |
|--------|---------|
| **Card advantage & selection** | Draw, impulse, scry, refill |
| **Counters & protection** | Stack interaction, free spells |
| **Removal & board** | Wipes, bounce, spot answers |
| **Damage & closers** | Burn, X finishers |
| **Extra turns** | Time walks |
| **Cost reduction** | Cheaper instants/sorceries (stacks with Mizzix) |
| **Ramp & mana** | Rocks, treasures, ritual mana |
| **Spell multipliers** | Storm, copies |
| **Recursion & yard** | Flashback, mastery, yard to hand |
| **Proliferate** | Extra counters on permanents/players |
| **Engines & bodies** | Creatures that reward spells |
| **Utility** | Lands and misc |

---

## Commander

| Card | Mana | Bucket | Role |
|------|------|--------|------|
| Mizzix of the Izmagnus | {2}{U}{R} | Engine | Experience when you cast high-MV instants/sorceries; **{1}** off each spell per counter (**generic** only). |

---

## Instants

### Card advantage & selection

| Card | Mana | Role |
|------|------|------|
| Drown in Dreams | {X}{2}{U} | Draw or mill for X; flexible X spell. |
| Experimental Augury | {1}{U} | Impulse 3 + proliferate. |
| Frantic Search | {2}{U} | Loot + untap lands. |
| Mystic Confluence | {3}{U}{U} | Three modes: draw / bounce / soft counter. |
| Thassa's Intervention | {X}{U}{U} | Impulse or tax counter. |
| Firemind's Foresight | {5}{U}{R} | Tutors instants with MV 3, 2, and 1. |

### Counters & protection

| Card | Mana | Role |
|------|------|------|
| Counterspell | {U}{U} | Hard counter. |
| Fierce Guardianship | {2}{U} | Often free with commander. |
| Fuel for the Cause | {2}{U}{U} | Counter + proliferate. |
| Mana Drain | {U}{U} | Counter + mana next main phase. |
| Power Sink | {X}{U} | X-based counter tax. |
| Rewind | {2}{U}{U} | Counter + untap lands. |
| Spell Burst | {X}{U} | Buyback counter for MV X. |
| Mystic Confluence | {3}{U}{U} | Counter mode (among others). |
| Thassa's Intervention | {X}{U}{U} | Tax counter mode. |

### Removal & board

| Card | Mana | Role |
|------|------|------|
| Aetherize | {3}{U} | Combat bounce all attackers. |
| Capsize | {1}{U}{U} | Bounce; buyback scales with discounts. |
| Cyclonic Rift | {1}{U} | Bounce; overload swings games. |
| Swan Song | {U} | Destroy artifact or enchantment. |

### Damage & closers

| Card | Mana | Role |
|------|------|------|
| Comet Storm | {X}{R}{R} | Multi-target X damage. |
| Electrodominance | {X}{R}{R} | Damage + may cast free spell from hand by MV. |

### Spell multipliers & copy

| Card | Mana | Role |
|------|------|------|
| Increasing Vengeance | {R}{R} | Copy your instant/sorcery; flashback. |
| Narset's Reversal | {U}{U} | Copy or hijack a spell. |
| Reiterate | {1}{R}{R} | Copy with buyback. |
| Storm King's Thunder | {X}{R}{R}{R} | Next instant/sorcery copied X times. |

### Recursion & yard

| Card | Mana | Role |
|------|------|------|
| Divergent Equation | {X}{X}{U} | Return up to X instants/sorceries from yard. |

### Proliferate (on instants)

| Card | Mana | Role |
|------|------|------|
| Radstorm | {3}{U} | Storm + proliferate. |
| Experimental Augury | {1}{U} | *(see CA)* |
| Fuel for the Cause | {2}{U}{U} | *(see counters)* |

### Mana & utility

| Card | Mana | Role |
|------|------|------|
| Turnabout | {2}{U}{U} | Untap lands / tap permanents / creature mode. |
| Deflecting Swat | {2}{R} | Redirect; often free with commander. |

---

## Sorceries

### Card advantage & selection

| Card | Mana | Role |
|------|------|------|
| Finale of Revelation | {X}{U}{U} | Draw X; high ceiling. |
| Mystic Speculation | {U} | Buyback scry 3. |
| Wisdom of Ages | {4}{U}{U}{U} | Return all instants/sorceries from yard; no max hand size. |

### Removal & board

| Card | Mana | Role |
|------|------|------|
| Blasphemous Act | {8}{R} | Sweeper; cost drops with creatures. |
| Bonfire of the Damned | {X}{X}{R} | Miracle / X damage. |
| Curse of the Swine | {X}{U}{U} | Exile creatures → Boars. |
| Hell to Pay | {X}{R} | Damage to creature + Treasures for overkill. |

### Damage & closers

| Card | Mana | Role |
|------|------|------|
| Crackle with Power | {X}{X}{X}{R}{R} | Triple-X burn. |
| Jaya's Immolating Inferno | {X}{R}{R} | Legendary sorcery — three targets. |

### Extra turns

| Card | Mana | Role |
|------|------|------|
| Time Stretch | {8}{U}{U} | Two extra turns. |

### Spell multipliers & chaos

| Card | Mana | Role |
|------|------|------|
| Epic Experiment | {X}{U}{R} | Exile top X, cast instants/sorceries free. |

### Recursion & yard

| Card | Mana | Role |
|------|------|------|
| Mizzix's Mastery | {3}{R} | Overload graveyard instants/sorceries. |

### Proliferate

| Card | Mana | Role |
|------|------|------|
| Expansion Algorithm | {X}{U}{U} | Proliferate X times. |

---

## Creatures

### Cost reduction

| Card | Mana | Role |
|------|------|------|
| Baral, Chief of Compliance | {1}{U} | Spells cost {1} less; loot on counter. |
| Ral, Monsoon Mage *(front)* | {1}{R} | Spells cost {1} less; transforms. |

### Engines & bodies

| Card | Mana | Role |
|------|------|------|
| Archmage Emeritus | {2}{U}{U} | Magecraft draw. |
| Flux Channeler | {2}{U} | Proliferate on noncreature spells. |
| Harmonic Prodigy | {1}{R} | Prowess; **doubles other Wizards’/Shamans’ triggered abilities** (see top of doc). |
| Katara, Waterbending Master | {1}{U} | Experience on opponents’-turn spells; attack to loot. |
| Prismari, the Inspiration | {5}{U}{R} | Your instants/sorceries have storm. |
| Storm-Kiln Artist | {3}{R} | Treasure on instants/sorceries. |
| Talrand, Sky Summoner | {2}{U}{U} | Drakes on instants/sorceries. |
| Veyran, Voice of Duality | {1}{U}{R} | Doubles spell damage and some combat triggers. |
| Vivi Ornitier | {1}{U}{R} | Mana by power; grows and pings on noncreatures. |

### Utility & combo

| Card | Mana | Role |
|------|------|------|
| Dirgur Focusmage *(prepare)* | {2}{U} | Discount + prepare; **Braingeyser** {X}{U}{U} from hand/yard per prepare rules. |
| Lier, Disciple of the Drowned | {3}{U}{U} | Flashback instants/sorceries from yard. |

---

## Artifacts

### Ramp & mana

| Card | Mana | Role |
|------|------|------|
| Sol Ring | {1} | Fast mana. |
| Arcane Signet | {2} | Fixing. |
| Bender's Waterskin | {3} | Any-color rock; untaps on others’ untap. |
| Resonating Lute | {2}{U}{R} | Lands add double mana **for instants/sorceries**; draw at 7+ cards. |

### Cost reduction & scaling

| Card | Mana | Role |
|------|------|------|
| Mindsplice Apparatus | {3}{U} | Oil counters: spells cost {1} less each. |
| Primal Amulet *(front)* | {4} | Spells cost {1} less; flips to Wellspring. |

### Protection

| Card | Mana | Role |
|------|------|------|
| Swiftfoot Boots | {2} | Hexproof + haste. |

---

## Enchantments

| Card | Mana | Role |
|------|------|------|
| Mystic Remora | {U} | Draw off opponents’ noncreature spells. |
| Rhystic Study | {2}{U} | Draw engine. |
| Propaganda | {2}{U} | Attack tax. |

---

## Lands (nonbasic)

| Card | Role |
|------|------|
| Arcane Lighthouse | {C}; removes hexproof/shroud from creature. |
| Cascade Bluffs | UR filter. |
| Command Beacon | Commander to hand ignoring tax. |
| Command Tower | Fixing. |
| Fiery Islet | UR; optional loot. |
| Mistrise Village | Island tap; pay U for uncounterable next spell. |
| Mystic Sanctuary | Island; bounce instant/sorcery to top. |
| Otawara, Soaring City | Channel bounce. |
| Prismatic Vista | Fetch basic. |
| Reliquary Tower | No max hand size. |
| Riptide Laboratory | Bounce wizards. |
| Riverglide Pathway // Lavaglide Pathway | MDFC U/R. |
| Scalding Tarn | Fetch. |
| Scorched Geyser | UR dual. |
| Shivan Reef | Pain dual. |
| Spirebluff Canal | Early-game untapped UR (condition: few lands). |
| Steam Vents | Shock. |
| Stormcarved Coast | Conditional untapped UR. |
| Sulfur Falls | Check dual. |
| Training Center | Bond land. |
| Turbulent Springs | UR dual. |
| Volcanic Island | Dual. |

**Basics:** Island ×11, Mountain ×3 (tuned to ~**68% / 32%** U/R pip share; see `decks/mizzix-spells.md`).

---

## Post-build checklist

- **Pip stress:** Many **{U}{U}** counters and **red** finishers — **Spirebluff Canal** + **11/3** basics better match **U:R** symbol ratio than **10/5**; utility lands unchanged.
- **Land optimization:** If **RRR** hands feel scarce, try **12 Island / 3 Mountain** (drop a **non-utility** dual you find least useful) — only after playtesting.
- **Counter density:** You have many answers; if the meta is low on stacks, you can eventually swap a **soft** piece (**Power Sink** / **Spell Burst**) for more velocity — only after data.
