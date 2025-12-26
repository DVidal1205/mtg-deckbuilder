"""
Root agent for MTG deckbuilder using Google ADK.

This agent provides access to card search functionality for building
Magic: The Gathering decks.
"""

import os

# Import tools - adjust path since we're in agents/root_agent/
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from google import adk
from google.adk.models.lite_llm import LiteLlm

# Add agents directory to path so we can import tools
agents_dir = Path(__file__).parent.parent
if str(agents_dir) not in sys.path:
    sys.path.insert(0, str(agents_dir))

from tools.search_cards import CardSearchFilters, search_cards

# Load environment variables from .env file (looks for .env in project root)
# Ensure your .env file contains: OPENROUTER_API_KEY=your_key_here
# Go up from agents/root_agent/agent.py to project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# Configure LiteLLM for OpenRouter
# Set environment variables for LiteLLM to use OpenRouter
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables. Please set it in your .env file.")
os.environ["OPENROUTER_API_KEY"] = openrouter_key
# Ensure LiteLLM uses OpenRouter API base
os.environ.setdefault("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")

# Default database path
DEFAULT_DB_PATH = "data/cards.db"

# Deck storage (in-memory for now, dummy implementation)
_deck: List[Dict[str, Any]] = []


def search_cards_tool(
    commander_ci: str,
    text_query: Optional[str],
    name_contains: Optional[str],
    type_contains_any: Optional[Sequence[str]],
    oracle_contains: Optional[Sequence[str]],
    cmc_min: Optional[float],
    cmc_max: Optional[float],
    colors_any: Optional[str],
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    """
    Search Magic: The Gathering cards in the local database.

    Essential search tool for finding MTG cards. All searches are automatically filtered to
    Commander-legal cards and sorted by EDHREC rank.

    Parameters:
        commander_ci: REQUIRED - Commander color identity restriction. Format: "UW" or "U,W" (W=White, U=Blue, B=Black, R=Red, G=Green).
          Example: "UG" finds cards legal in Simic (blue-green) commander decks.
          Use "" (empty string) if you want to search all colors.
        text_query: Optional - Full-text search query. Best for searching card abilities/text.
          Searches name, type_line, oracle_text, and face_oracle_texts. Pass null if not needed.
          Example: "draw a card" finds cards with that text.
        name_contains: Optional - Search for cards by name (case-insensitive substring). Pass null if not needed.
          Example: "Lightning" finds "Lightning Bolt", "Lightning Strike", etc.
        type_contains_any: Optional - List of type substrings to match. Finds cards that are ANY of these types. Pass null if not needed.
          Example: ["Creature", "Artifact"] finds cards that are Creatures OR Artifacts.
        oracle_contains: Optional - List of phrases to search in oracle text. Finds cards matching ANY phrase. Pass null if not needed.
          Example: ["draw a card", "enters the battlefield"] finds cards with either phrase.
        cmc_min: Optional - Minimum converted mana cost (inclusive). Use float values (e.g., 2.0). Pass null if not needed.
        cmc_max: Optional - Maximum converted mana cost (inclusive). Use float values (e.g., 4.0). Pass null if not needed.
        colors_any: Optional - Card colors to match. Format: "UW" or "U,W". Pass null if not needed.
          Example: "UG" finds blue and/or green cards.
        limit: Optional - Maximum number of results to return. Default is 5 if null or not specified.

    Returns:
        List of card dictionaries. Each dictionary contains:
        - name: Card name
        - mana_cost: Mana cost (e.g., "{1}{U}")
        - cmc: Converted mana cost
        - type_line: Card type (e.g., "Creature — Human Wizard")
        - oracle_text: Card text/abilities
        - colors: Card colors (comma-separated, e.g., "U,W")
        - color_identity: Commander color identity (comma-separated)
        - rarity: Card rarity
        - edhrec_rank: EDHREC rank (lower is more popular)
        - price_usd: USD price
        - keywords: Card keywords (comma-separated)
        - mechanic_tags: Custom mechanic tags (comma-separated)
        - image_normal: Card image URL
        - scryfall_uri: Scryfall page URL

    Examples:
        # Find a card by name in UG colors
        search_cards_tool(commander_ci="UG", name_contains="Hakbal", limit=5)

        # Find creatures with specific mana cost in UG colors
        search_cards_tool(commander_ci="UG", type_contains_any=["Creature"], cmc_min=1.0, cmc_max=3.0, limit=10)

        # Find cards that draw cards in UG colors
        search_cards_tool(commander_ci="UG", text_query="draw a card", limit=10)

        # Find cards with multiple oracle text phrases in UG colors
        search_cards_tool(commander_ci="UG", oracle_contains=["draw a card", "enters the battlefield"], limit=15)

        # Search all colors (use empty string)
        search_cards_tool(commander_ci="", name_contains="Lightning", limit=5)
    """
    # Set defaults
    if limit is None:
        limit = 5

    # Handle empty string for commander_ci (search all colors)
    commander_ci_filter = commander_ci if commander_ci and commander_ci.strip() else None

    # Use absolute path relative to project root
    project_root = Path(__file__).parent.parent.parent
    db_path = str(project_root / DEFAULT_DB_PATH)

    filters = CardSearchFilters(
        text_query=text_query,
        name_contains=name_contains,
        type_contains_any=type_contains_any,
        oracle_contains=oracle_contains,
        cmc_min=cmc_min,
        cmc_max=cmc_max,
        colors_any=colors_any,
        commander_ci=commander_ci_filter,
        legal_format="commander",
        legal_value="legal",
        rarity=None,
        set_code=None,
        price_usd_max=None,
        keywords_any=None,
        mechanic_tags_any=None,
        limit=limit,
        offset=0,
        order_by="edhrec_rank",
        order_dir="ASC",
    )

    return search_cards(db_path=db_path, filters=filters, select_fields=None)


def insert_to_deck(
    card_name: str,
    mana_cost: Optional[str],
    type_line: Optional[str],
    oracle_text: Optional[str],
    colors: Optional[str],
    color_identity: Optional[str],
    cmc: Optional[float],
) -> Dict[str, Any]:
    """
    Add a card to the current deck.

    This tool allows you to add cards to the deck being built. The deck is maintained
    as a sorted list of cards. Each card includes its name, mana cost, type line,
    oracle text, and color information.

    Args:
        card_name: The name of the card to add (required).
        mana_cost: The mana cost of the card (e.g., "{1}{U}").
        type_line: The card's type line (e.g., "Creature — Human Wizard").
        oracle_text: The card's oracle text/abilities.
        colors: The card's colors (comma-separated, e.g., "U,W").
        color_identity: The card's color identity for Commander (comma-separated, e.g., "U,W").
        cmc: The converted mana cost of the card.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the card was added
        - message: Status message
        - deck: List of cards in the deck, sorted by name. Each card includes:
          - name: Card name
          - mana_cost: Mana cost
          - type_line: Type line
          - oracle_text: Oracle text
          - colors: Colors
          - color_identity: Color identity
          - cmc: Converted mana cost
        - deck_count: Total number of cards in the deck
    """
    global _deck

    # Create card entry (handle None values)
    card_entry = {
        "name": card_name,
        "mana_cost": mana_cost if mana_cost is not None else "",
        "type_line": type_line if type_line is not None else "",
        "oracle_text": oracle_text if oracle_text is not None else "",
        "colors": colors if colors is not None else "",
        "color_identity": color_identity if color_identity is not None else "",
        "cmc": cmc if cmc is not None else 0.0,
    }

    # Check if card already exists (by name containment)
    # Check if new card name is contained in existing card name or vice versa
    existing_index = None
    card_name_lower = card_name.lower()
    for i, card in enumerate(_deck):
        existing_name_lower = card["name"].lower()
        # Check if either name contains the other (case-insensitive)
        if card_name_lower in existing_name_lower or existing_name_lower in card_name_lower:
            existing_index = i
            break

    if existing_index is not None:
        # Card already exists, update it
        _deck[existing_index] = card_entry
        message = f"Updated card '{card_name}' in deck"
    else:
        # Add new card, but first check if the deck is full
        if len(_deck) >= 100:
            return {
                "success": False,
                "message": "Deck is full. Please present the deck to the user and ask them to remove a card before adding a new one.",
                "deck": _deck.copy(),
                "deck_count": len(_deck),
            }
        _deck.append(card_entry)
        message = f"Added '{card_name}' to deck"

    # Sort deck by card name
    _deck.sort(key=lambda x: x["name"].lower())

    # Print deck state
    print("\n" + "=" * 80)
    print(f"DECK STATE ({len(_deck)} cards)")
    print("=" * 80)
    for i, card in enumerate(_deck, 1):
        print(f"\n{i}. {card['name']}")
        if card["mana_cost"]:
            print(f"   Mana Cost: {card['mana_cost']}")
        if card["type_line"]:
            print(f"   Type: {card['type_line']}")
        if card["colors"]:
            print(f"   Colors: {card['colors']}")
        if card["color_identity"]:
            print(f"   Color Identity: {card['color_identity']}")
        if card["cmc"]:
            print(f"   CMC: {card['cmc']}")
        if card["oracle_text"]:
            # Print oracle text with indentation, wrapping long lines
            oracle_lines = card["oracle_text"].split("\n")
            print("   Oracle Text:")
            for line in oracle_lines:
                print(f"     {line}")
    print("\n" + ("=" * 80) + "\n")

    return {
        "success": True,
        "message": message,
        "deck": _deck.copy(),  # Return a copy to avoid external modification
        "deck_count": len(_deck),
    }


# Create the root agent - this will be picked up by adk web
# Using LiteLLM with OpenRouter to access NVIDIA model that supports tools
# Note: Use a model that supports function calling/tools on OpenRouter
# Format: openrouter/provider/model-name
# Try using a model that explicitly supports tools, or use OpenAI-compatible NVIDIA model
OPENROUTER_MODEL = "openrouter/openai/gpt-oss-120b"

root_agent = adk.Agent(
    model=LiteLlm(model=OPENROUTER_MODEL),
    name="root_agent",
    instruction=(
        "You are a helpful assistant for building Magic: The Gathering decks. "
        "You can search for cards using the search_cards_tool to help users find "
        "cards that fit their deck strategy, color identity, budget, and other criteria. "
        "When searching for cards, be specific about the user's requirements and use "
        "appropriate filters to find the most relevant results. "
        "You can add cards to the deck using the insert_to_deck tool. When a user wants to "
        "add a card, use the card information from search results to insert it with all "
        "relevant fields (name, mana_cost, type_line, oracle_text, colors, color_identity, cmc)."
    ),
    tools=[search_cards_tool, insert_to_deck],
)
