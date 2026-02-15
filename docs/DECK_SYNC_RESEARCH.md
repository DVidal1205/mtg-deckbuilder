# Moxfield Sync — API Research & Known Limitations

## Working Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v2/users/{username}/decks?pageNumber=1&pageSize=200` | List user's **public** decks |
| GET | `/v3/decks/all/{publicId}` | Full deck object (cards, boards, version) |
| POST | `/v3/decks` | Create empty deck (`{"name", "format", "visibility"}`) |
| POST | `/v2/decks/{internalId}/import` | Import/append cards (`{"importText": "1 Sol Ring\n..."}`) |

**Important:** The `import` endpoint **appends** — it does NOT replace existing cards.

## Known Limitations

### No deck deletion via API
- `DELETE /v2/decks/{id}` → 405 Method Not Allowed
- `DELETE /v3/decks/{id}` → 404

### No card removal via API (yet)
- `PUT /v2/decks/{internalId}/cards/{board}/{uniqueCardId}` with `{"quantity":0}` → 400 "quantity must be > 0"
- The Moxfield web UI **can** delete cards (sends a PUT with `x-deck-version` + `x-public-deck-id` headers)
- Our API calls with the same headers still get 400 — likely a Cloudflare or session issue
- **TODO:** Capture the actual request **payload** (not just headers) from DevTools when deleting a card in the UI

### Visibility
- Newly created decks must be `"visibility": "public"` to appear in the `/v2/users/{username}/decks` listing
- Private decks are invisible to the listing endpoint

## Sync Strategy

Since we can't delete or replace, the tool uses this approach:

1. **First sync:** Create deck → Import cards ✓
2. **Re-sync (no changes):** Compare remote vs local → Skip if identical ✓
3. **Re-sync (changed):** Create **new** deck with same name → Import → Update `.md` metadata
   - Old deck left intact (user deletes manually on Moxfield)

## Authentication

- Uses **Bearer token** (JWT) from the `Authorization` header
- Extract from browser: F12 → Network → any `api2.moxfield.com` request → Authorization header
- Tokens expire periodically — re-extract when you get 403 errors
- Set via: `export MOXFIELD_BEARER_TOKEN="eyJ..."`

## Cloudflare

- Moxfield is behind Cloudflare; plain `requests` library gets 403
- Tool uses `curl_cffi` with `impersonate="chrome"` to bypass
- `cf_clearance` cookie may be needed for some write operations (unconfirmed)

## Key Data Model Notes

- Each deck has a **publicId** (URL-friendly, e.g. `296iUZy-SU-dWA6iFuR1Rg`) and an **internal id** (short, e.g. `d3Z0xw`)
- Write endpoints use the **internal id**; read endpoints accept either
- Cards in boards are keyed by `uniqueCardId` (not Scryfall ID)
- The `x-deck-version` header tracks optimistic concurrency
