from pyedhrec import EDHRec

edhrec = EDHRec()

# Reference cards by the exact card name, the library will format as needed
miirym = "Miirym, Sentinel Wyrm"

# Get basic card details
details = edhrec.get_card_details(miirym)

# Get details for a list of cards
card_list = edhrec.get_card_list(["Pongify", "Farseek"])

# Get an edhrec.com link for a given card
miirym_link = edhrec.get_card_link(miirym)

# Get combos for a card
miirym_combos = edhrec.get_card_combos(miirym)

# Get commander data
miirym_commander_data = edhrec.get_commander_data(miirym)

# Get cards commonly associated with a commander
miirym_cards = edhrec.get_commander_cards(miirym)

# Get the average decklist for a commander
miirym_avg_deck = edhrec.get_commanders_average_deck(miirym)

# Get known deck lists for a commander
miirym_decks = edhrec.get_commander_decks(miirym)

# This library provides several methods to get specific types of recommended cards
new_cards = edhrec.get_new_cards(miirym)
high_synergy_cards = edhrec.get_high_synergy_cards(miirym)

# Get all top cards
top_cards = edhrec.get_top_cards(miirym)

# Get specific top cards by type
top_creatures = edhrec.get_top_creatures(miirym)
top_instants = edhrec.get_top_instants(miirym)
top_sorceries = edhrec.get_top_sorceries(miirym)
top_enchantments = edhrec.get_top_enchantments(miirym)
top_artifacts = edhrec.get_top_artifacts(miirym)
top_mana_artifacts = edhrec.get_top_mana_artifacts(miirym)
top_battles = edhrec.get_top_battles(miirym)
top_planeswalkers = edhrec.get_top_planeswalkers(miirym)
top_utility_lands = edhrec.get_top_utility_lands(miirym)
top_lands = edhrec.get_top_lands(miirym)


print(top_cards)
