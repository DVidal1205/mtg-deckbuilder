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

# Add agents directory to path so we can import tools
agents_dir = Path(__file__).parent.parent
if str(agents_dir) not in sys.path:
    sys.path.insert(0, str(agents_dir))

from tools.search_cards import CardSearchFilters, search_cards

# Load environment variables from .env file (looks for .env in project root)
# Ensure your .env file contains: OPENROUTER_API_KEY=your_key_here
# Go up from agents/root_agent/root_agent.py to project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# Configure LiteLLM for OpenRouter
# Google ADK will use LiteLLM automatically when it sees "openrouter/" model prefix
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables. Please set it in your .env file.")
os.environ["OPENROUTER_API_KEY"] = openrouter_key

# Default database path
DEFAULT_DB_PATH = "data/cards.db"


def search_cards_tool(
    text_query: Optional[str] = None,
    name_contains: Optional[str] = None,
    type_contains_any: Optional[Sequence[str]] = None,
    oracle_contains: Optional[str] = None,
    cmc_min: Optional[float] = None,
    cmc_max: Optional[float] = None,
    colors_any: Optional[str] = None,
    commander_ci: Optional[str] = None,
    legal_format: Optional[str] = None,
    legal_value: str = "legal",
    rarity: Optional[str] = None,
    set_code: Optional[str] = None,
    price_usd_max: Optional[float] = None,
    keywords_any: Optional[Sequence[str]] = None,
    mechanic_tags_any: Optional[Sequence[str]] = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "edhrec_rank",
    order_dir: str = "ASC",
    db_path: Optional[str] = None,
    select_fields: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search Magic: The Gathering cards in the local database.

    This tool allows you to search for MTG cards using various filters including:
    - Full-text search across card names, types, and oracle text
    - Filter by mana cost, colors, color identity (for Commander)
    - Filter by format legality, rarity, set, price
    - Filter by keywords and mechanic tags
    - Sort and paginate results

    Args:
        text_query: Full-text search query (searches name, type_line, oracle_text, face_oracle_texts)
        name_contains: Substring match on card name
        type_contains_any: List of type substrings (e.g., ["Creature", "Artifact"])
        oracle_contains: Substring match on oracle text
        cmc_min: Minimum converted mana cost (inclusive)
        cmc_max: Maximum converted mana cost (inclusive)
        colors_any: Colors to match (e.g., "UW" or "U,W" for blue and white)
        commander_ci: Commander color identity restriction (e.g., "UW" for Azorius)
        legal_format: Format name (e.g., "commander", "standard")
        legal_value: Legality value (default: "legal")
        rarity: Rarity filter (common, uncommon, rare, mythic, special)
        set_code: Scryfall set code (e.g., "MH3", "BRO")
        price_usd_max: Maximum USD price
        keywords_any: List of keywords to match (e.g., ["Flying", "Vigilance"])
        mechanic_tags_any: List of mechanic tags to match (e.g., ["blink", "aristocrats"])
        limit: Maximum number of results (default: 50)
        offset: Pagination offset (default: 0)
        order_by: Sort field (edhrec_rank, cmc, price_usd, name, released_at)
        order_dir: Sort direction (ASC or DESC)
        db_path: Path to SQLite database (defaults to "data/cards.db")
        select_fields: Optional list of specific fields to return

    Returns:
        List of card dictionaries with card information
    """
    if db_path is None:
        # Use absolute path relative to project root
        # Go up from agents/root_agent/root_agent.py to project root
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
        commander_ci=commander_ci,
        legal_format=legal_format,
        legal_value=legal_value,
        rarity=rarity,
        set_code=set_code,
        price_usd_max=price_usd_max,
        keywords_any=keywords_any,
        mechanic_tags_any=mechanic_tags_any,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )

    return search_cards(db_path=db_path, filters=filters, select_fields=select_fields)


# Create the root agent - this will be picked up by adk web
# Using LiteLLM with OpenRouter to access NVIDIA Nemotron model
root_agent = adk.Agent(
    model="openrouter/nvidia/nemotron-4-340b-instruct",  # NVIDIA Nemotron via OpenRouter
    name="root_agent",
    instruction=(
        "You are a helpful assistant for building Magic: The Gathering decks. "
        "You can search for cards using the search_cards_tool to help users find "
        "cards that fit their deck strategy, color identity, budget, and other criteria. "
        "When searching for cards, be specific about the user's requirements and use "
        "appropriate filters to find the most relevant results."
    ),
    tools=[search_cards_tool],
)
