# DEVLOG

This log is by no means complete or professional, but just a quick place to document the development of the project.

## 2025-12-26

-   Started the project
-   Created the base structure of the project
-   Downloaded the main cards.json file from Scryfall on the [Bulk Data page](https://scryfall.com/docs/api/bulk-data) page
-   Wrote `convert.py` to convert the cards.json file to a more manageable csv format
-   Downloaded each of the tag types from EDHRec [Tags page](https://edhrec.com/tags/themes) to get a better understanding of the card synergy
-   Update: EDHRec cards are a bit useless and stupid. Instead using some shaky regex to infer tags and have LLM confirm during deck building.
