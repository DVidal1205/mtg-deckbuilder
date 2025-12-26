#!/usr/bin/env python3
"""
Convert Scryfall card JSON data to pandas DataFrame for EDA.

This script reads cards.json and converts it to a pandas DataFrame,
flattening nested structures and handling various card types including
multiface cards.
"""

import json
import re
from typing import Any, Dict, List

import pandas as pd

# TAG_RULES v1 (Tier 1)
# Notes:
# - These are intended to run against your "rules blob" (type_line + oracle_text + face fields + keywords string).
# - Keep them fairly broad in v1; you’ll tune with sampling.
# - Some tags are better DERIVED at query-time (ex: aristocrats) but I included light direct patterns too.
# - Use re.IGNORECASE when searching.

TAG_RULES = {
    # ----------------------------
    # Tokens / Counters / Board
    # ----------------------------
    "tokens": [
        r"\bcreate\b.*\btoken(s)?\b",
        r"\btoken(s)?\b.*\b(you control|under your control)\b",
        r"\bpopulate\b",
    ],
    "counters_plus1": [
        r"\+\s*1\s*/\s*\+\s*1\s*counter(s)?",
        r"\bput\b.*\+\s*1\s*/\s*\+\s*1\s*counter(s)?\b",
        r"\bwith\s+an?\s+\+\s*1\s*/\s*\+\s*1\s*counter\b",
        r"\b(enter|enters)\b.*\bwith\b.*\+\s*1\s*/\s*\+\s*1\s*counter",
    ],
    "counters_minus1": [
        r"-\s*1\s*/\s*-\s*1\s*counter(s)?",
        r"\bput\b.*-\s*1\s*/\s*-\s*1\s*counter(s)?\b",
        r"\bwith\s+an?\s+-\s*1\s*/\s*-\s*1\s*counter\b",
        r"\b(enter|enters)\b.*\bwith\b.*-\s*1\s*/\s*-\s*1\s*counter",
    ],
    "anthems": [
        r"\bcreatures?\s+you\s+control\s+get\s+\+\d+/\+\d+\b",
        r"\bother\s+creatures?\s+you\s+control\s+get\s+\+\d+/\+\d+\b",
        r"\bcreatures?\s+you\s+control\s+have\b.*\b(get|gain)\b",
        r"\bother\s+creatures?\s+you\s+control\s+have\b",
    ],
    # ----------------------------
    # Blink / ETB / Sac / Dies
    # ----------------------------
    "blink": [
        # Classic flicker wording
        r"\bexile\b.*\b(then|and)\b.*\breturn\b.*\bto\s+the\s+battlefield\b",
        r"\bexile\b.*\breturn\b.*\bto\s+the\s+battlefield\b.*\bunder\b.*\bcontrol\b",
        # Blink a permanent you control
        r"\bexile\b\s+(another\s+)?target\s+.*\byou\s+control\b",
        # Temporarily exile and return at EOT
        r"\bexile\b.*\breturn\b.*\bat\s+the\s+beginning\s+of\s+the\s+next\s+end\s+step\b",
    ],
    "etb": [
        r"\benters\s+the\s+battlefield\b",
        r"\bwhen\b.*\benters\s+the\s+battlefield\b",
        r"\bwhenever\b.*\benters\s+the\s+battlefield\b",
        r"\bwhen\b.*\benter(s)?\s+the\s+battlefield\b",
    ],
    "sac_outlet": [
        # Activated outlet: "Sacrifice a creature: ..."
        r"\bsacrifice\b\s+(an?\s+)?(artifact|creature|enchantment|land|permanent)\s*:",
        r"\bsacrifice\b\s+(another\s+)?(artifact|creature|enchantment|land|permanent)\s*:",
        # Broad outlet forms
        r"\bsacrifice\b\s+(an?\s+)?(artifact|creature|enchantment|land|permanent)\b.*:",
        r"\bsacrifice\b\s+(another\s+)?(artifact|creature|enchantment|land|permanent)\b.*:",
        # "As an additional cost to cast this spell, sacrifice ..."
        r"\bas\s+an\s+additional\s+cost\b.*\bsacrifice\b",
    ],
    "dies_payoff": [
        r"\bwhen(ever)?\b.*\bdies\b",
        r"\bwhen(ever)?\b.*\bis\s+put\s+into\s+a\s+graveyard\s+from\s+the\s+battlefield\b",
        r"\bwhenever\b.*\ba\s+creature\b.*\bdies\b",
        r"\bwhenever\b.*\banother\b.*\bdies\b",
    ],
    # You can derive "aristocrats" at query-time as: sac_outlet OR dies_payoff (or both).
    # Keeping a light direct tag can still help.
    "aristocrats": [
        r"\bwhenever\b.*\bdies\b.*\b(each opponent|target player)\b.*\b(lose|loses)\b.*\blife\b",
        r"\bwhenever\b.*\byou\s+sacrifice\b",
        r"\b(sacrifice|dies)\b.*\bdrain\b",
    ],
    # ----------------------------
    # Graveyard / Reanimator / Mill / Discard / Wheels
    # ----------------------------
    "reanimator": [
        r"\breturn\b\s+target\b.*\bcard\b.*\bfrom\s+your\s+graveyard\b.*\bto\s+the\s+battlefield\b",
        r"\bput\b\s+target\b.*\bcard\b.*\bfrom\s+(a|any|your)\s+graveyard\b.*\bonto\s+the\s+battlefield\b",
        r"\breturn\b\s+up\s+to\s+\w+\s+target\b.*\bcard(s)?\b.*\bfrom\s+your\s+graveyard\b.*\bto\s+the\s+battlefield\b",
        r"\breturn\b\s+all\b.*\bcreature\s+cards?\b.*\bfrom\s+your\s+graveyard\b.*\bto\s+the\s+battlefield\b",
    ],
    "graveyard_matters": [
        r"\bfrom\s+your\s+graveyard\b",
        r"\bin\s+your\s+graveyard\b",
        r"\byour\s+graveyard\b",
        r"\bexile\b.*\bfrom\s+your\s+graveyard\b",
        r"\breturn\b.*\bfrom\s+your\s+graveyard\b.*\bto\s+your\s+hand\b",
    ],
    "self_mill": [
        r"\bput\b\s+the\s+top\s+\w+\s+cards?\s+of\s+your\s+library\s+into\s+your\s+graveyard\b",
        r"\bmill\b\s+yourself\b",
        r"\byou\b\s+mill\b",
    ],
    "mill": [
        r"\bmill\b",
        r"\bput\b\s+the\s+top\s+\w+\s+cards?\s+of\s+.*\s+library\s+into\s+.*\s+graveyard\b",
        r"\bputs?\b\s+the\s+top\s+\w+\s+cards?\s+of\s+.*\s+library\s+into\s+.*\s+graveyard\b",
    ],
    "discard": [
        r"\btarget\b.*\bdiscards?\b",
        r"\beach\b.*\bdiscards?\b",
        r"\bopponent(s)?\b.*\bdiscards?\b",
    ],
    "wheels": [
        r"\beach\s+player\b.*\bdiscards?\b.*\bthen\b.*\bdraws?\b",
        r"\bdiscard\s+your\s+hand\b.*\bthen\b.*\bdraws?\b",
        r"\bshuffle\b.*\bhand\b.*\binto\b.*\blibrary\b.*\bthen\b.*\bdraws?\b",
    ],
    # ----------------------------
    # Spells / Copy / Storm
    # ----------------------------
    "spellslinger": [
        r"\binstant\s+or\s+sorcery\b",
        r"\bnoncreature\s+spell\b",
        r"\bwhenever\b.*\byou\s+cast\b.*\bspell\b",
        r"\bwhenever\b.*\byou\s+cast\b.*\binstant\b",
        r"\bwhenever\b.*\byou\s+cast\b.*\bsorcery\b",
    ],
    "spell_copy": [
        r"\bcopy\b\s+target\b.*\bspell\b",
        r"\bcopy\b\s+target\b.*\binstant\b",
        r"\bcopy\b\s+target\b.*\bsorcery\b",
        r"\bcreate\b\s+a\s+copy\b",
        r"\bcreate\b\s+.*\bcopies\b",
    ],
    "storm": [
        r"\bstorm\b",
        r"\bgravestorm\b",
        # “When you cast this spell, copy it for each ...”
        r"\bwhen\b\s+you\s+cast\s+this\s+spell\b.*\bcopy\b.*\bfor\s+each\b",
    ],
    # ----------------------------
    # Lands
    # ----------------------------
    "lands_matter": [
        r"\bwhenever\b.*\ba\s+land\b.*\benters\s+the\s+battlefield\b.*\bunder\s+your\s+control\b",
        r"\bplay\b\s+an\s+additional\s+land\b",
        r"\byou\s+may\s+play\s+\w+\s+additional\s+lands?\b",
        r"\blands?\s+you\s+control\b",
        r"\bsearch\b\s+your\s+library\b.*\bfor\b.*\bland\b",
    ],
    "landfall_like": [
        r"\bwhenever\b.*\ba\s+land\b.*\benters\s+the\s+battlefield\b.*\bunder\s+your\s+control\b",
        r"\blandfall\b",  # if present in oracle blob/keywords string; harmless if you later exclude keyword-only tagging
    ],
    "land_destruction": [
        r"\bdestroy\b\s+target\s+land\b",
        r"\bexile\b\s+target\s+land\b",
        r"\beach\b.*\bsacrifice\b.*\bland\b",
        r"\bplayers?\b.*\bcan'?t\b.*\bplay\b.*\blands?\b",
    ],
    # ----------------------------
    # Permanent-type themes
    # ----------------------------
    "artifacts_matter": [
        r"\bartifact(s)?\b.*\byou\s+control\b",
        r"\baffinity\b.*\bartifacts?\b",
        r"\bmetalcraft\b",
        r"\bwhenever\b.*\bartifact\b",
        r"\bfor\s+each\b.*\bartifact\b",
    ],
    "enchantress": [
        r"\bwhenever\b.*\byou\s+cast\b.*\benchantment\s+spell\b",
        r"\bwhenever\b.*\ban?\s+enchantment\b.*\benters\s+the\s+battlefield\b.*\bunder\s+your\s+control\b",
        r"\bconstellation\b",
    ],
    "auras_matter": [
        r"\baura\b",
        r"\benchanted\s+creature\b",
        r"\baura\s+spell\b",
        r"\battach\b.*\baura\b",
    ],
    "equipment_matter": [
        r"\bequipment\b",
        r"\bequipped\s+creature\b",
        r"\battach\b.*\bequipment\b",
    ],
    "vehicles_matter": [
        r"\bvehicle\b",
        r"\bcrew\b",
    ],
    "sagas_matter": [
        r"\bsaga\b",
        r"\bchapter\b\s+\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b",
    ],
    "planeswalkers_matter": [
        r"\bplaneswalker\b",
        r"\bloyalty\b",
        r"\badd\b\s+(\+|-)\d+\b.*\bloyalty\b",
    ],
    "clones": [
        r"\bcopy\b.*\bcreature\b.*\bexcept\b",
        r"\benters\s+the\s+battlefield\b.*\bas\b\s+a\s+copy\b",
        r"\byou\s+may\s+have\b.*\benter\s+the\s+battlefield\b.*\bas\b\s+a\s+copy\b",
    ],
    # ----------------------------
    # Interaction / Win packages
    # ----------------------------
    "theft": [
        r"\bgain\s+control\s+of\b",
        r"\buntil\s+end\s+of\s+turn\b.*\bgain\s+control\s+of\b",
        r"\bsteal\b",  # rare in oracle text but harmless
    ],
    "burn": [
        r"\bdeals?\b\s+\w+\s+damage\b",
        r"\bdeal\b\s+\w+\s+damage\b",
        r"\bdamage\b\s+to\s+(any\s+target|target\s+player|each\s+opponent|each\s+creature)\b",
    ],
    "infect": [
        r"\binfect\b",
        r"\bpoison\s+counter(s)?\b",
        r"\btoxic\b",
    ],
    # ----------------------------
    # Stax / Hatebears / Fort
    # ----------------------------
    "stax": [
        r"\bplayers?\b\s+can'?t\b",
        r"\bopponents?\b\s+can'?t\b",
        r"\bcan'?t\b\s+cast\b",
        r"\bcan'?t\b\s+activate\b",
        r"\bskip\b\s+your\b",
        r"\bcosts?\b.*\bmore\s+to\s+cast\b",
    ],
    "hatebears": [
        # creature-based restriction tends to show in oracle, but we’ll approximate via restriction language.
        # You can tighten later by also requiring "creature" in type_line at runtime.
        r"\bplayers?\b\s+can'?t\b",
        r"\bopponents?\b\s+can'?t\b",
        r"\bcosts?\b.*\bmore\s+to\s+cast\b",
        r"\bnoncreature\b.*\bspells?\b.*\bcost\b.*\bmore\b",
    ],
    "pillow_fort": [
        r"\bcreatures?\b\s+can'?t\s+attack\s+you\b",
        r"\bcreatures?\b\s+can'?t\s+attack\s+you\s+or\s+planeswalkers?\b",
        r"\bcan'?t\s+attack\s+you\b\s+unless\b",
        r"\bunless\b.*\bpay\b.*\bfor\s+each\s+creature\b.*\battacking\s+you\b",
        r"\bprevent\b.*\ball\b.*\bcombat\s+damage\b.*\bthat\s+would\b.*\bdeal\b.*\byou\b",
    ],
    # ----------------------------
    # Combat direction / extra phases
    # ----------------------------
    "forced_combat": [
        r"\bmust\s+attack\b",
        r"\bgoad\b",
        r"\battacks?\s+each\s+combat\b",
        r"\bcan'?t\s+block\b",
    ],
    "extra_turns": [
        r"\btake\s+an?\s+extra\s+turn\b",
        r"\bextra\s+turn\s+after\s+this\s+one\b",
    ],
    "extra_combats": [
        r"\ban?\s+additional\s+combat\s+phase\b",
        r"\badditional\s+combat\s+phase\b",
        r"\buntap\b.*\bafter\s+this\s+combat\b.*\bthere\s+is\b.*\ban?\s+additional\s+combat\b",
    ],
    # ----------------------------
    # Voltron / Social
    # ----------------------------
    "voltron": [
        r"\bequipped\s+creature\b",
        r"\benchanted\s+creature\b",
        r"\bwhen\b.*\bthis\b.*\bdeals\s+combat\s+damage\s+to\b",  # typical voltron payoff text
        r"\bdouble\s+strike\b.*\b(trample|lifelink|hexproof|indestructible)\b",  # heuristic
    ],
    "group_hug": [
        r"\beach\s+player\b.*\bdraws?\b",
        r"\beach\s+player\b.*\bmay\b.*\bdraw\b",
        r"\bwhenever\b.*\ban?\s+opponent\b.*\bdraws?\b",
        r"\badd\b.*\bfor\s+each\s+player\b",  # loose heuristic
    ],
    "group_slug": [
        r"\beach\s+opponent\b.*\bloses?\b.*\blife\b",
        r"\beach\s+player\b.*\bloses?\b.*\blife\b",
        r"\bwhenever\b.*\bcasts?\b.*\blose\b.*\blife\b",
        r"\bat\s+the\s+beginning\s+of\b.*\beach\s+player\b.*\bloses?\b.*\blife\b",
    ],
    "politics": [
        r"\bchoose\s+an?\s+opponent\b",
        r"\btarget\s+opponent\b\s+chooses\b",
        r"\bany\s+number\s+of\s+target\s+players?\b",
        r"\bfor\s+each\s+opponent\b.*\bchoose\b",
        r"\bvote\b",
        r"\bwill\s+of\s+the\s+council\b",
        r"\bcouncil'?s\s+dilemma\b",
    ],
}


def build_rules_blob(flattened: Dict[str, Any]) -> str:
    """
    Build a single searchable string representing the card's rules-relevant text.
    Includes face data when present.
    """
    parts: List[str] = []
    for k in ["type_line", "oracle_text", "keywords", "face_type_lines", "face_oracle_texts"]:
        v = flattened.get(k)
        if v:
            parts.append(str(v))
    return "\n".join(parts).lower()


def compute_mechanic_tags(flattened: Dict[str, Any]) -> str:
    """
    Compute mechanic tags for a flattened card row using TAG_RULES.
    Returns a comma-separated string of unique tags (sorted).
    """
    if not TAG_RULES:
        return ""

    text = build_rules_blob(flattened)
    if not text:
        return ""

    tags: List[str] = []
    for tag, patterns in TAG_RULES.items():
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                tags.append(tag)
                break

    tags = sorted(set(tags))
    return ",".join(tags)


def flatten_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten a card object for DataFrame conversion.

    Handles nested dictionaries (prices, legalities, image_uris, etc.)
    and converts lists to comma-separated strings.
    """
    flattened: Dict[str, Any] = {}

    # Copy simple fields as-is
    simple_fields = [
        "object",
        "id",
        "oracle_id",
        "name",
        "lang",
        "released_at",
        "uri",
        "scryfall_uri",
        "layout",
        "highres_image",
        "image_status",
        "mana_cost",
        "cmc",
        "type_line",
        "oracle_text",
        "power",
        "toughness",
        "defense",
        "loyalty",
        "hand_modifier",
        "life_modifier",
        "collector_number",
        "digital",
        "rarity",
        "watermark",
        "flavor_text",
        "flavor_name",
        "card_back_id",
        "artist",
        "illustration_id",
        "border_color",
        "frame",
        "security_stamp",
        "full_art",
        "textless",
        "booster",
        "story_spotlight",
        "edhrec_rank",
        "penny_rank",
        "game_changer",
        "foil",
        "nonfoil",
        "oversized",
        "promo",
        "reprint",
        "variation",
        "reserved",
        "content_warning",
        "set_id",
        "set",
        "set_name",
        "set_type",
        "set_uri",
        "set_search_uri",
        "scryfall_set_uri",
        "rulings_uri",
        "prints_search_uri",
        "arena_id",
        "mtgo_id",
        "mtgo_foil_id",
        "tcgplayer_id",
        "tcgplayer_etched_id",
        "cardmarket_id",
        "resource_id",
        "variation_of",
        "printed_name",
        "printed_text",
        "printed_type_line",
    ]

    for field in simple_fields:
        if field in card:
            flattened[field] = card[field]

    # Handle multiverse_ids (list) - take first or join as string
    if "multiverse_ids" in card and card["multiverse_ids"]:
        flattened["multiverse_id"] = card["multiverse_ids"][0]
        flattened["multiverse_ids"] = ",".join(map(str, card["multiverse_ids"]))

    # Handle colors (list) - convert to comma-separated string
    if "colors" in card:
        flattened["colors"] = ",".join(card["colors"]) if card["colors"] else ""
        flattened["color_count"] = len(card["colors"]) if card["colors"] else 0

    # Handle color_identity (list)
    if "color_identity" in card:
        flattened["color_identity"] = ",".join(card["color_identity"]) if card["color_identity"] else ""
        flattened["color_identity_count"] = len(card["color_identity"]) if card["color_identity"] else 0

    # Handle color_indicator (list)
    if "color_indicator" in card and card["color_indicator"]:
        flattened["color_indicator"] = ",".join(card["color_indicator"])

    # Handle keywords (list)
    if "keywords" in card:
        flattened["keywords"] = ",".join(card["keywords"]) if card["keywords"] else ""
        flattened["keyword_count"] = len(card["keywords"]) if card["keywords"] else 0

    # Handle games (list)
    if "games" in card:
        flattened["games"] = ",".join(card["games"]) if card["games"] else ""

    # Handle finishes (list)
    if "finishes" in card:
        flattened["finishes"] = ",".join(card["finishes"]) if card["finishes"] else ""

    # Handle frame_effects (list)
    if "frame_effects" in card:
        flattened["frame_effects"] = ",".join(card["frame_effects"]) if card["frame_effects"] else ""

    # Handle promo_types (list)
    if "promo_types" in card:
        flattened["promo_types"] = ",".join(card["promo_types"]) if card["promo_types"] else ""

    # Handle produced_mana (list)
    if "produced_mana" in card and card["produced_mana"]:
        flattened["produced_mana"] = ",".join(card["produced_mana"])
        flattened["produced_mana_count"] = len(card["produced_mana"])

    # Handle attraction_lights (list)
    if "attraction_lights" in card and card["attraction_lights"]:
        flattened["attraction_lights"] = ",".join(str(light) for light in card["attraction_lights"])
        flattened["attraction_lights_count"] = len(card["attraction_lights"])

    # Handle artist_ids (list) - take first or join
    if "artist_ids" in card and card["artist_ids"]:
        flattened["artist_id"] = card["artist_ids"][0]
        flattened["artist_ids"] = ",".join(card["artist_ids"])

    # Flatten prices dictionary
    if "prices" in card and card["prices"]:
        prices = card["prices"]
        flattened["price_usd"] = prices.get("usd")
        flattened["price_usd_foil"] = prices.get("usd_foil")
        flattened["price_usd_etched"] = prices.get("usd_etched")
        flattened["price_eur"] = prices.get("eur")
        flattened["price_eur_foil"] = prices.get("eur_foil")
        flattened["price_eur_etched"] = prices.get("eur_etched")
        flattened["price_tix"] = prices.get("tix")

    # Flatten legalities dictionary
    if "legalities" in card and card["legalities"]:
        for format_name, legality in card["legalities"].items():
            flattened[f"legal_{format_name}"] = legality

    # Flatten image_uris dictionary - keep main image URL
    if "image_uris" in card and card["image_uris"]:
        image_uris = card["image_uris"]
        flattened["image_small"] = image_uris.get("small")
        flattened["image_normal"] = image_uris.get("normal")
        flattened["image_large"] = image_uris.get("large")
        flattened["image_png"] = image_uris.get("png")
        flattened["image_art_crop"] = image_uris.get("art_crop")
        flattened["image_border_crop"] = image_uris.get("border_crop")

    # Handle preview dictionary
    if "preview" in card and card["preview"]:
        preview = card["preview"]
        flattened["preview_source"] = preview.get("source")
        flattened["preview_source_uri"] = preview.get("source_uri")
        flattened["preview_previewed_at"] = preview.get("previewed_at")

    # Flatten related_uris dictionary
    if "related_uris" in card and card["related_uris"]:
        related_uris = card["related_uris"]
        flattened["related_uri_gatherer"] = related_uris.get("gatherer")
        flattened["related_uri_tcgplayer_infinite_articles"] = related_uris.get("tcgplayer_infinite_articles")
        flattened["related_uri_tcgplayer_infinite_decks"] = related_uris.get("tcgplayer_infinite_decks")
        flattened["related_uri_edhrec"] = related_uris.get("edhrec")
        flattened["related_uri_mtgtop8"] = related_uris.get("mtgtop8")

    # Flatten purchase_uris dictionary
    if "purchase_uris" in card and card["purchase_uris"]:
        purchase_uris = card["purchase_uris"]
        flattened["purchase_uri_tcgplayer"] = purchase_uris.get("tcgplayer")
        flattened["purchase_uri_cardmarket"] = purchase_uris.get("cardmarket")
        flattened["purchase_uri_cardhoarder"] = purchase_uris.get("cardhoarder")

    # Handle all_parts (list of related cards) - store as JSON string or count
    if "all_parts" in card and card["all_parts"]:
        flattened["all_parts_count"] = len(card["all_parts"])
        # Store related card names as comma-separated string
        flattened["related_card_names"] = ",".join([part.get("name", "") for part in card["all_parts"]])
        flattened["related_card_components"] = ",".join([part.get("component", "") for part in card["all_parts"]])
        flattened["related_card_type_lines"] = ",".join([part.get("type_line", "") for part in card["all_parts"]])

    # Handle card_faces (multiface cards) - store key info
    if "card_faces" in card and card["card_faces"]:
        faces = card["card_faces"]
        flattened["card_faces_count"] = len(faces)
        # Store face names
        flattened["face_names"] = " // ".join([face.get("name", "") for face in faces])
        # Store face mana costs
        flattened["face_mana_costs"] = " // ".join([face.get("mana_cost", "") for face in faces])
        # Store face types
        flattened["face_type_lines"] = " // ".join([face.get("type_line", "") for face in faces])
        # Store face oracle text
        flattened["face_oracle_texts"] = " // ".join([face.get("oracle_text", "") for face in faces])
        # Store face colors
        face_colors = []
        for face in faces:
            if face.get("colors"):
                face_colors.append(",".join(face["colors"]))
            else:
                face_colors.append("")
        flattened["face_colors"] = " // ".join(face_colors)
        # Store face color indicators
        face_color_indicators = []
        for face in faces:
            if face.get("color_indicator"):
                face_color_indicators.append(",".join(face["color_indicator"]))
            else:
                face_color_indicators.append("")
        flattened["face_color_indicators"] = " // ".join(face_color_indicators)
        # Store face artists
        flattened["face_artists"] = " // ".join([face.get("artist", "") for face in faces])
        # Store face watermarks
        face_watermarks = []
        for face in faces:
            face_watermarks.append(face.get("watermark", ""))
        flattened["face_watermarks"] = " // ".join(face_watermarks)
        # Store face powers/toughnesses
        face_pt = []
        for face in faces:
            power = face.get("power", "")
            toughness = face.get("toughness", "")
            if power or toughness:
                face_pt.append(f"{power}/{toughness}" if power and toughness else (power or toughness))
            else:
                face_pt.append("")
        flattened["face_power_toughness"] = " // ".join(face_pt)
        # Store face loyalties
        face_loyalties = []
        for face in faces:
            face_loyalties.append(face.get("loyalty", ""))
        flattened["face_loyalties"] = " // ".join(face_loyalties)
        # Store face defenses
        face_defenses = []
        for face in faces:
            face_defenses.append(face.get("defense", ""))
        flattened["face_defenses"] = " // ".join(face_defenses)
        # Store face CMCs (for reversible cards)
        face_cmcs = []
        for face in faces:
            if face.get("cmc") is not None:
                face_cmcs.append(str(face["cmc"]))
            else:
                face_cmcs.append("")
        flattened["face_cmcs"] = " // ".join(face_cmcs)
        # Store face flavor texts
        flattened["face_flavor_texts"] = " // ".join([face.get("flavor_text", "") for face in faces])
        # Store face printed names
        flattened["face_printed_names"] = " // ".join([face.get("printed_name", "") for face in faces])
        # Store face printed texts
        flattened["face_printed_texts"] = " // ".join([face.get("printed_text", "") for face in faces])
        # Store face printed type lines
        flattened["face_printed_type_lines"] = " // ".join([face.get("printed_type_line", "") for face in faces])

    # -----------------------------------------------------------------------
    # Compute mechanic tags (Option A) and store as CSV-friendly string
    # -----------------------------------------------------------------------
    flattened["mechanic_tags"] = compute_mechanic_tags(flattened)
    flattened["mechanic_tag_count"] = len(flattened["mechanic_tags"].split(",")) if flattened["mechanic_tags"] else 0

    return flattened


def convert_to_dataframe(json_file: str) -> pd.DataFrame:
    """
    Convert cards.json to pandas DataFrame.

    Args:
        json_file: Path to cards.json file

    Returns:
        pandas DataFrame with flattened card data
    """
    print(f"Loading {json_file}...")
    with open(json_file, "r", encoding="utf-8") as f:
        cards = json.load(f)

    print(f"Found {len(cards)} cards. Flattening data...")

    # Flatten all cards
    flattened_cards = [flatten_card(card) for card in cards]

    # Convert to DataFrame
    df = pd.DataFrame(flattened_cards)

    print(f"DataFrame created with shape: {df.shape}")
    print(f"Columns: {len(df.columns)}")

    return df


def main():
    """Main function to convert cards.json to DataFrame."""
    import sys

    json_file = "data/cards.json"
    if len(sys.argv) > 1:
        json_file = sys.argv[1]

    # Convert to DataFrame
    df = convert_to_dataframe(json_file)

    # Display basic info
    print("\n" + "=" * 50)
    print("DataFrame Info:")
    print("=" * 50)
    print(df.info())

    print("\n" + "=" * 50)
    print("First few rows:")
    print("=" * 50)
    print(df.head())

    print("\n" + "=" * 50)
    print("Column names:")
    print("=" * 50)
    print(list(df.columns))

    # Save to CSV (optional)
    output_file = json_file.replace(".json", ".csv")
    print(f"\nSaving to {output_file}...")
    df.to_csv(output_file, index=False)
    print(f"Saved to {output_file}")

    return df


if __name__ == "__main__":
    df = main()
