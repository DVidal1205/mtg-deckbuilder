# Import cards.json as a list of blobs
import json

with open("data/cards.json", "r") as f:
    cards = json.load(f)

# Print the number of cards
print(len(cards))

# Print the unique fields in the cards
print(set(cards[0].keys()))

# Analyze the primitive count of each mana in each mana_cost
mana_counts = {}

for card in cards:
    if "mana_cost" in card:
        mana_cost = card["mana_cost"]
        mana_cost = mana_cost.replace("{", "").replace("}", "")
        if "/" in mana_cost:
            pass
        else:
            for mana in mana_cost:
                mana_counts[mana] = mana_counts.get(mana, 0) + 1

mana_counts = sorted(mana_counts.items(), key=lambda x: x[1], reverse=True)
print(mana_counts)

# Analyze the counts of each mana combination in each mana_cost
mana_combinations = {}

for card in cards:
    if "mana_cost" in card:
        mana_cost = card["mana_cost"]
        if "/" in mana_cost or mana_cost == "":
            pass
        else:
            mana_cost = mana_cost.replace("{", "").replace("}", "")
            mana_cost = mana_cost.split(" ")
            mana_cost.sort()
            mana_cost = "".join(mana_cost)
            mana_combinations[mana_cost] = mana_combinations.get(mana_cost, 0) + 1

mana_combinations = sorted(mana_combinations.items(), key=lambda x: x[1], reverse=True)
singles = mana_combinations[0]
for combo in mana_combinations:
    print(combo)

# Find count of cards with cmc = ""
land_count = 0
for card in cards:
    if "type_line" in card:
        type_line = card["type_line"]
        if "Land" in type_line:
            land_count += 1
print(land_count)

# Find the count of valid commanders
# A commander is either a legendary creature, or a card with "can be your commander" in the oracle text
commander_count = 0
commander_cards = []
for card in cards:
    if "type_line" in card:
        type_line = card["type_line"]
        if "Legendary" in type_line:
            commander_count += 1
    if "oracle_text" in card:
        oracle_text = card["oracle_text"]
        if "can be your commander" in oracle_text:
            commander_count += 1
            commander_cards.append(card)
print(commander_count)
# print 25 random commanders
import random

random.shuffle(commander_cards)
for card in commander_cards[:25]:
    print(card["name"])

# Print a set of unique values in keywords
keywords = set()
for card in cards:
    if "keywords" in card:
        keywords_list = card["keywords"]
        for keyword in keywords_list:
            keywords.add(keyword)
print(len(keywords))
print(sorted(keywords))
