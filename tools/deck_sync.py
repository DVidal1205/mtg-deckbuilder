#!/usr/bin/env python3
"""
deck_sync.py — Sync local decks to Moxfield.

Reads decks from the local `decks/` folder and pushes them to Moxfield.
On first sync a deck is created; on subsequent syncs the deck is updated
in-place via the bulk-edit endpoint (full card replacement, no duplicates).

The Moxfield deck ID is stored in the deck's .md metadata so the tool
knows which Moxfield deck corresponds to which local file.

Credentials are loaded from .env (MOXFIELD_BEARER_TOKEN, MOXFIELD_USERNAME).

Usage:
    python tools/deck_sync.py --all              # sync every deck in decks/
    python tools/deck_sync.py decks/hakbal.md    # sync one deck
    python tools/deck_sync.py --all --dry-run    # preview without touching Moxfield
    python tools/deck_sync.py --list-remote      # show decks on Moxfield
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import curl_cffi.requests

# ── Load .env ────────────────────────────────────────────────────────────────

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def _load_dotenv():
    """Load .env file into os.environ (no external deps needed)."""
    if not _ENV_PATH.exists():
        return
    try:
        with open(_ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key:
                    # Always set from .env (allows override via explicit env vars if needed)
                    os.environ[key] = value
    except Exception:
        pass  # Silently fail if .env can't be read

_load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────

MOXFIELD_USERNAME = os.environ.get("MOXFIELD_USERNAME", "DVidal1205")
API_BASE = "https://api2.moxfield.com"
MOXFIELD_WEB = "https://www.moxfield.com"
MOXFIELD_VERSION = "2026.02.16.1"

DECKS_DIR = Path(__file__).resolve().parent.parent / "decks"


# ── Deck parsing ────────────────────────────────────────────────────────────

def parse_decklist(filepath: str) -> Tuple[Dict[str, str], List[Tuple[int, str]]]:
    """Parse a .md deck file → (metadata dict, [(count, card_name), ...])."""
    metadata: Dict[str, str] = {}
    cards: List[Tuple[int, str]] = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    title_m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_m:
        metadata["deck"] = title_m.group(1).strip()

    for m in re.finditer(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|', content):
        metadata[m.group(1).strip().lower()] = m.group(2).strip()

    fence = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)
    for fm in fence.finditer(content):
        for line in fm.group(1).strip().split("\n"):
            line = line.strip()
            cm = re.match(r'^(\d+)\s+(.+)$', line)
            if cm:
                cards.append((int(cm.group(1)), cm.group(2).strip()))
        break

    return metadata, cards


# ── Moxfield API wrapper ────────────────────────────────────────────────────

class MoxfieldAPI:
    """Thin wrapper around the Moxfield REST API via curl_cffi (bypasses Cloudflare)."""

    def __init__(self, bearer_token: str):
        self.token = bearer_token
        self._base_headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "x-moxfield-version": MOXFIELD_VERSION,
            "origin": "https://moxfield.com",
            "referer": "https://moxfield.com/",
        }

    def _get(self, path: str) -> dict:
        r = curl_cffi.requests.get(
            f"{API_BASE}{path}",
            headers=self._base_headers,
            impersonate="chrome",
            timeout=15,
        )
        if r.status_code == 401:
            raise RuntimeError(f"401 Unauthorized on GET {path} – Bearer token may be expired or invalid")
        if r.status_code == 403:
            raise RuntimeError("403 Forbidden – Bearer token may be expired")
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> curl_cffi.requests.Response:
        return curl_cffi.requests.post(
            f"{API_BASE}{path}",
            headers=self._base_headers,
            json=body,
            impersonate="chrome",
            timeout=15,
        )

    # ── public ───────────────────────────────────────────────────────────

    def list_user_decks(self, username: str = MOXFIELD_USERNAME) -> List[dict]:
        """Return list of deck summaries for a user."""
        data = self._get(f"/v2/users/{username}/decks?pageNumber=1&pageSize=200")
        return data.get("data", [])

    def get_deck(self, public_id: str) -> dict:
        """Return full deck object by publicId."""
        return self._get(f"/v3/decks/all/{public_id}")

    def create_deck(self, name: str, fmt: str = "commander") -> dict:
        """Create an empty deck (public so it appears in user listings). Returns the new deck object."""
        r = self._post("/v3/decks", {"name": name, "format": fmt, "visibility": "public"})
        if r.status_code == 403:
            raise RuntimeError("403 Forbidden – Bearer token may be expired")
        r.raise_for_status()
        return r.json()

    def import_cards(self, internal_id: str, decklist_text: str) -> dict:
        """
        Append cards to a deck via the bulk-import endpoint.
        Uses the **internal id** (short, e.g. 'JrQQDg'), NOT the publicId.
        NOTE: This APPENDS. Use bulk_edit() for full replacement.
        """
        r = self._post(f"/v2/decks/{internal_id}/import", {"importText": decklist_text})
        if r.status_code == 403:
            raise RuntimeError("403 Forbidden – Bearer token may be expired")
        r.raise_for_status()
        return r.json()

    def bulk_edit(
        self, public_id: str, version: int, commander_text: str, mainboard_text: str
    ) -> dict:
        """
        **FULL DECK REPLACEMENT** — clears all cards and replaces with the given lists.

        Uses PUT /v3/decks/{publicId}/bulk-edit with per-board text.
        Requires x-deck-version for optimistic concurrency.

        Args:
            public_id:      The deck's publicId (URL-safe, e.g. '296iUZy-SU-dWA6iFuR1Rg')
            version:        Current deck version (from GET response)
            commander_text: Newline-delimited card list for commanders zone
            mainboard_text: Newline-delimited card list for mainboard zone
        """
        headers = {
            **self._base_headers,
            "x-deck-version": str(version),
            "x-public-deck-id": public_id,
        }
        body = {
            "boards": {
                "commanders": commander_text,
                "mainboard": mainboard_text,
            }
        }
        r = curl_cffi.requests.put(
            f"{API_BASE}/v3/decks/{public_id}/bulk-edit",
            headers=headers,
            json=body,
            impersonate="chrome",
            timeout=30,
        )
        if r.status_code == 401:
            error_detail = r.text[:500] if r.text else "No error message"
            raise RuntimeError(f"401 Unauthorized on PUT bulk-edit {public_id} – Response: {error_detail}")
        if r.status_code == 403:
            raise RuntimeError("403 Forbidden – Bearer token may be expired")
        r.raise_for_status()
        return r.json()

    def move_to_commanders(self, public_id: str, commander_name: str) -> bool:
        """
        Move a card from mainboard to the commanders zone.

        Fetches the deck, finds the commander by name in the mainboard,
        and POSTs it to the commanders zone.  Moxfield automatically
        removes the mainboard copy when the POST succeeds.

        Returns True on success (or if already in the right zone).
        """
        try:
            full = self.get_deck(public_id)
        except Exception as e:
            print(f"  ⚠ Failed to fetch deck for commander assignment: {e}")
            return False

        internal_id = full.get("id")
        version = full.get("version", 1)

        # Check if commander is already in command zone
        cmdr_board = full.get("boards", {}).get("commanders", {}).get("cards", {})
        already_in_zone = False
        for _uid, entry in cmdr_board.items():
            if entry.get("card", {}).get("name", "").lower() == commander_name.lower():
                already_in_zone = True
                break

        # Find the commander in the mainboard
        mb = full.get("boards", {}).get("mainboard", {}).get("cards", {})
        card_id = None
        card_name_found = None
        in_mainboard = False
        for _uid, entry in mb.items():
            name = entry.get("card", {}).get("name", "")
            if name.lower() == commander_name.lower():
                card_id = entry.get("card", {}).get("id")
                card_name_found = name
                in_mainboard = True
                break

        # If not in mainboard and already in zone, we're done
        if already_in_zone and not in_mainboard:
            print(f"  ✓ Commander already in command zone (not in mainboard)")
            return True

        # If in mainboard but not in zone, move it
        if in_mainboard and not already_in_zone:
            if not card_id:
                print(f"  ⚠ Commander '{commander_name}' found in mainboard but no cardId")
                return False

            print(f"  → Moving '{card_name_found}' (cardId={card_id}) to command zone...")
            headers = {
                **self._base_headers,
                "x-deck-version": str(version),
                "x-public-deck-id": public_id,
            }
            try:
                r = curl_cffi.requests.post(
                    f"{API_BASE}/v2/decks/{internal_id}/cards/commanders",
                    headers=headers,
                    json={"cardId": card_id, "quantity": 1},
                    impersonate="chrome",
                    timeout=10,
                )
                if r.status_code not in (200, 201):
                    print(f"  ⚠ Commander POST returned {r.status_code}: {r.text[:200]}")
                    return False
                print(f"  ✓ POST succeeded (status {r.status_code})")
                # Fetch updated deck for cleanup step
                try:
                    full = self.get_deck(public_id)
                    version = full.get("version", version + 1)
                except Exception as e:
                    print(f"  ⚠ Failed to fetch deck after move: {e}")
                    return True
            except Exception as e:
                print(f"  ⚠ Commander POST failed: {e}")
                return False
        elif in_mainboard and already_in_zone:
            print(f"  → Commander in command zone but also in mainboard — removing duplicate")

        # Remove commander from mainboard (whether we just moved it or it was already there)
        if in_mainboard:
            mb_current = full.get("boards", {}).get("mainboard", {}).get("cards", {})
            mainboard_lines = []
            for _uid, entry in mb_current.items():
                name = entry.get("card", {}).get("name", "")
                qty = entry.get("quantity", 1)
                if name.lower() != commander_name.lower():
                    mainboard_lines.append(f"{qty} {name}")

            mainboard_text = "\n".join(mainboard_lines)
            try:
                self.bulk_edit(public_id, version, "", mainboard_text)
                print(f"  ✓ Removed commander from mainboard")
            except Exception as e:
                print(f"  ⚠ Failed to remove commander from mainboard: {e}")

        return True

    def deck_matches_local(
        self, public_id: str, local_cards: List[Tuple[int, str]], commander: str = ""
    ) -> bool:
        """Check whether a remote deck's card list AND commander zone match the local one."""
        try:
            full = self.get_deck(public_id)
        except Exception:
            return False

        # Check card totals across mainboard + commanders
        remote_cards: Dict[str, int] = {}
        for board_name in ("mainboard", "commanders"):
            board = full.get("boards", {}).get(board_name, {}).get("cards", {})
            for _uid, entry in board.items():
                name = entry.get("card", {}).get("name", "")
                qty = entry.get("quantity", 0)
                remote_cards[name.lower()] = remote_cards.get(name.lower(), 0) + qty

        local_map: Dict[str, int] = {}
        for qty, name in local_cards:
            local_map[name.lower()] = local_map.get(name.lower(), 0) + qty

        if remote_cards != local_map:
            return False

        # Also verify the commander is in the commanders zone (not just mainboard)
        if commander:
            cmdr_board = full.get("boards", {}).get("commanders", {}).get("cards", {})
            cmdr_names = [
                e.get("card", {}).get("name", "").lower() for e in cmdr_board.values()
            ]
            if commander.lower() not in cmdr_names:
                return False  # Commander is in wrong zone → needs re-sync

        return True


# ── Metadata helpers (read/write Moxfield ID in .md files) ──────────────────

MOXFIELD_META_RE = re.compile(
    r'^\|\s*\*\*Moxfield\s+ID\*\*\s*\|\s*(.+?)\s*\|', re.MULTILINE,
)
MOXFIELD_NAME_RE = re.compile(
    r'^\|\s*\*\*Moxfield\s+Name\*\*\s*\|\s*(.+?)\s*\|', re.MULTILINE,
)


def read_moxfield_meta(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """Read stored Moxfield publicId and Moxfield deck name from a .md file."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    pid = MOXFIELD_META_RE.search(text)
    mname = MOXFIELD_NAME_RE.search(text)
    pid_val = pid.group(1).strip() if pid else None
    mname_val = mname.group(1).strip() if mname else None
    # Treat empty or pipe-only values as None
    if pid_val in (None, "", "|"):
        pid_val = None
    if mname_val in (None, "", "|"):
        mname_val = None
    return (pid_val, mname_val)


def write_moxfield_meta(filepath: str, public_id: str, moxfield_name: str):
    """Insert or update the Moxfield ID and Moxfield Name rows in the metadata table."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    new_id = f"| **Moxfield ID** | {public_id} |"
    new_name = f"| **Moxfield Name** | {moxfield_name} |"

    if MOXFIELD_META_RE.search(text):
        text = MOXFIELD_META_RE.sub(new_id, text)
    else:
        text = re.sub(r'(\|\s*\*\*Date\*\*\s*\|.+?\|)', r'\1\n' + new_id, text, count=1)

    if MOXFIELD_NAME_RE.search(text):
        text = MOXFIELD_NAME_RE.sub(new_name, text)
    else:
        text = text.replace(new_id, new_id + "\n" + new_name)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


# ── Core sync logic ─────────────────────────────────────────────────────────

def sync_one_deck(
    api: MoxfieldAPI,
    filepath: str,
    remote_decks: List[dict],
    dry_run: bool = False,
) -> bool:
    """
    Sync a single local deck to Moxfield.

    Flow:
      1. Parse local .md file.
      2. Look for stored Moxfield ID in metadata → if found, verify it exists remotely.
      3. If remote deck exists AND card lists match → skip (already up-to-date).
      4. If remote deck exists but cards differ → create a NEW deck (import is append-only).
      5. If no remote deck → create + import.
      6. Write new Moxfield ID + Name back into the .md metadata.
    """
    metadata, cards = parse_decklist(filepath)
    deck_title = metadata.get("deck", Path(filepath).stem)
    commander = metadata.get("commander", "")
    stored_pid, stored_mname = read_moxfield_meta(filepath)
    mox_name = stored_mname or deck_title

    # ── Validate card count ──────────────────────────────────────────────
    total_cards = sum(c for c, _ in cards)
    if total_cards != 100:
        print(f"  ✗ Card count is {total_cards} (must be exactly 100 for Commander) — skipping")
        return False

    # ── Resolve remote deck ──────────────────────────────────────────────
    remote = None
    if stored_pid:
        for rd in remote_decks:
            if rd.get("publicId") == stored_pid:
                remote = rd
                break
        if remote is None:
            print(f"  ⚠ Stored Moxfield ID {stored_pid} not found remotely")
    if remote is None:
        for rd in remote_decks:
            if rd.get("name", "").lower() == mox_name.lower():
                remote = rd
                break

    # ── Check if already up-to-date ──────────────────────────────────────
    if remote and not dry_run:
        if api.deck_matches_local(remote["publicId"], cards, commander):
            print(f"  ✓ Already up-to-date: {mox_name}")
            # Make sure metadata is saved
            write_moxfield_meta(filepath, remote["publicId"], mox_name)
            return True

    # ── Dry run ──────────────────────────────────────────────────────────
    if dry_run:
        action = "UP-TO-DATE?" if remote else "CREATE"
        if remote:
            action = "CHECK/UPDATE"
        rid = remote.get("publicId", "—") if remote else "—"
        print(f"  [{action}] {deck_title}")
        print(f"    Moxfield name : {mox_name}")
        print(f"    Moxfield ID   : {rid}")
        print(f"    Commander     : {commander}")
        print(f"    Cards         : {sum(c for c, _ in cards)} total, {len(cards)} unique")
        return True

    # ── Build card text ──────────────────────────────────────────────────
    # ALL cards go into mainboard first (including commander).
    # After bulk_edit, we move the commander to the commanders zone via
    # a separate POST.  This guarantees the commander is always present
    # in the deck even if the move step fails.
    mainboard_lines = [f"{count} {name}" for count, name in cards]
    mainboard_text = "\n".join(mainboard_lines)

    # ── Update existing or create new ────────────────────────────────────
    if remote:
        public_id = remote["publicId"]
        print(f"  Updating \"{mox_name}\" in-place ({public_id})")

        # Get version for optimistic concurrency
        full = api.get_deck(public_id)
        version = full.get("version", 1)

        result = api.bulk_edit(public_id, version, "", mainboard_text)
    else:
        print(f"  Creating new Moxfield deck: \"{mox_name}\"")
        new_deck = api.create_deck(mox_name, "commander")
        public_id = new_deck.get("publicId")
        internal_id = new_deck.get("id")

        if public_id and not internal_id:
            full = api.get_deck(public_id)
            internal_id = full.get("id")

        if not public_id or not internal_id:
            print(f"  ✗ Create failed – unexpected response: {new_deck}")
            return False

        # New deck: use bulk-edit to set everything at once
        full = api.get_deck(public_id)
        version = full.get("version", 1)
        result = api.bulk_edit(public_id, version, "", mainboard_text)

    # ── Move commander from mainboard → commanders zone ──────────────────
    if commander:
        if api.move_to_commanders(public_id, commander):
            print(f"  ✓ Commander → command zone: {commander}")
        else:
            print(f"  ⚠ Commander may not be in the command zone — check Moxfield")

    # ── Report results ───────────────────────────────────────────────────
    board_errors = result.get("errors", {})
    if isinstance(board_errors, dict):
        for board_name, errs in board_errors.get("boards", {}).items():
            if errs:
                print(f"  ⚠ {board_name} warnings: {errs[:3]}")

    deck_url = f"{MOXFIELD_WEB}/decks/{public_id}"
    card_count = sum(c for c, _ in cards)
    print(f"  ✓ Synced {card_count} cards → {deck_url}")

    write_moxfield_meta(filepath, public_id, mox_name)
    return True


# ── Pull (Moxfield → local) ──────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert a deck name to a filename slug."""
    s = name.lower().strip()
    s = re.sub(r"[''']", "", s)            # remove apostrophes
    s = re.sub(r"[^a-z0-9]+", "-", s)      # non-alphanum → dash
    s = s.strip("-")
    return s


def pull_deck(api: MoxfieldAPI, public_id: str, name: str) -> str:
    """
    Download a Moxfield deck and write it as a local .md file.

    Returns the path of the created file.
    """
    full = api.get_deck(public_id)

    # ── Extract commander ────────────────────────────────────────────────
    cmdr_board = full.get("boards", {}).get("commanders", {}).get("cards", {})
    commander_name = ""
    commander_lines: List[str] = []
    for _uid, entry in cmdr_board.items():
        cname = entry.get("card", {}).get("name", "")
        qty = entry.get("quantity", 1)
        commander_lines.append(f"{qty} {cname}")
        if not commander_name:
            commander_name = cname

    # ── Extract mainboard ────────────────────────────────────────────────
    mb_board = full.get("boards", {}).get("mainboard", {}).get("cards", {})
    mainboard_lines: List[str] = []
    for _uid, entry in mb_board.items():
        cname = entry.get("card", {}).get("name", "")
        qty = entry.get("quantity", 1)
        mainboard_lines.append(f"{qty} {cname}")

    all_card_lines = commander_lines + mainboard_lines
    total = sum(int(l.split()[0]) for l in all_card_lines)

    # ── Extract color identity ───────────────────────────────────────────
    ci = full.get("colorIdentity", [])
    ci_str = "".join(sorted(ci)).upper() if ci else "?"

    # ── Build .md content ────────────────────────────────────────────────
    today = __import__("datetime").date.today().isoformat()
    # Use deck name for slug (not commander) to avoid collisions
    # when multiple decks share the same commander
    slug = slugify(name)
    filepath = DECKS_DIR / f"{slug}.md"

    # If file already exists, don't overwrite
    if filepath.exists():
        # Check if it's the same Moxfield deck
        existing_pid, _ = read_moxfield_meta(str(filepath))
        if existing_pid != public_id:
            # Different deck — add suffix to avoid collision
            i = 2
            while filepath.exists():
                filepath = DECKS_DIR / f"{slug}-{i}.md"
                i += 1

    lines = [
        f"# {name}",
        "",
        "| | |",
        "|---|---|",
        f"| **Commander** | {commander_name} |",
        f"| **Color Identity** | {ci_str} |",
        f"| **Date** | {today} |",
        f"| **Moxfield ID** | {public_id} |",
        f"| **Moxfield Name** | {name} |",
        "",
        "## Strategy",
        "",
        "_Imported from Moxfield — add strategy notes here._",
        "",
        "## Decklist",
        "",
        "```",
    ]
    lines.extend(commander_lines)
    lines.extend(mainboard_lines)
    lines.append("```")
    lines.append("")

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(filepath)


def pull_remote_decks(api: MoxfieldAPI, names: Optional[List[str]] = None):
    """Pull decks from Moxfield → local .md files."""
    remote_decks = api.list_user_decks()
    print(f"Found {len(remote_decks)} deck(s) on Moxfield\n")

    # Check which decks already have local files (by Moxfield ID)
    existing_ids: set = set()
    for fp in DECKS_DIR.glob("*.md"):
        pid, _ = read_moxfield_meta(str(fp))
        if pid:
            existing_ids.add(pid)

    pulled = 0
    skipped = 0
    for rd in remote_decks:
        rname = rd.get("name", "?")
        rpid = rd.get("publicId", "")

        # Filter by name if specified
        if names and not any(n.lower() in rname.lower() for n in names):
            continue

        if rpid in existing_ids:
            print(f"  ⏭ {rname} — already linked locally, skipping")
            skipped += 1
            continue

        print(f"  ↓ Pulling \"{rname}\" ({rpid})...")
        try:
            fp = pull_deck(api, rpid, rname)
            total_line = sum(
                int(l.split()[0])
                for l in open(fp).read().split("```")[1].strip().split("\n")
                if re.match(r"^\d+\s+", l)
            )
            print(f"    ✓ {total_line} cards → {fp}")
            pulled += 1
        except Exception as e:
            print(f"    ✗ Error: {e}")

    print(f"\nPulled {pulled}, skipped {skipped}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def get_all_deck_files() -> List[str]:
    if not DECKS_DIR.exists():
        return []
    return sorted(str(p) for p in DECKS_DIR.glob("*.md"))


def main():
    parser = argparse.ArgumentParser(
        description="Sync local MTG decks to Moxfield",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="Sync every deck in decks/")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--list-remote", action="store_true", help="List Moxfield decks and exit")
    parser.add_argument("--pull", nargs="*", metavar="NAME",
                        help="Pull decks FROM Moxfield → local .md files. "
                             "No args = pull all unlinked decks. "
                             "Provide name(s) to filter.")
    parser.add_argument("deck_files", nargs="*", help="Specific deck file(s) to sync")
    args = parser.parse_args()

    bearer = os.environ.get("MOXFIELD_BEARER_TOKEN")
    if not bearer:
        print("Error: MOXFIELD_BEARER_TOKEN not set.", file=sys.stderr)
        if _ENV_PATH.exists():
            print(f"  .env file exists at {_ENV_PATH} but token not loaded.", file=sys.stderr)
            print("  Check that .env contains: MOXFIELD_BEARER_TOKEN=eyJ...", file=sys.stderr)
        else:
            print(f"  .env file not found at {_ENV_PATH}", file=sys.stderr)
            print("  Create .env with:", file=sys.stderr)
            print("    MOXFIELD_BEARER_TOKEN=eyJ...", file=sys.stderr)
            print("    MOXFIELD_USERNAME=DVidal1205", file=sys.stderr)
        print("\nTo get a fresh token:", file=sys.stderr)
        print("  1. Open moxfield.com → F12 → Network tab", file=sys.stderr)
        print("  2. Make any request to api2.moxfield.com", file=sys.stderr)
        print('  3. Copy the Authorization header value (after "Bearer ")', file=sys.stderr)
        print("  4. Update .env file with the new token", file=sys.stderr)
        return 1

    api = MoxfieldAPI(bearer)

    if args.pull is not None:
        print(f"Pulling decks from Moxfield for {MOXFIELD_USERNAME}...")
        pull_remote_decks(api, args.pull if args.pull else None)
        return 0

    if args.list_remote:
        print(f"Moxfield decks for {MOXFIELD_USERNAME}:\n")
        try:
            decks = api.list_user_decks()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        for d in decks:
            print(f"  {d['name']:<30s}  id={d['publicId']}  fmt={d.get('format','?')}")
        print(f"\n{len(decks)} deck(s) total")
        return 0

    if args.all:
        deck_files = get_all_deck_files()
    elif args.deck_files:
        deck_files = args.deck_files
    else:
        parser.error("Specify --all, --list-remote, or provide deck file(s)")

    if not deck_files:
        print("No deck files found.", file=sys.stderr)
        return 1

    print(f"Fetching Moxfield decks for {MOXFIELD_USERNAME}...")
    try:
        remote_decks = api.list_user_decks()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Bearer token may be expired — extract a fresh one.", file=sys.stderr)
        return 1
    print(f"Found {len(remote_decks)} deck(s) on Moxfield\n")

    if args.dry_run:
        print("── DRY RUN (no changes) ──\n")

    ok = 0
    fail = 0
    for fp in deck_files:
        if not os.path.exists(fp):
            print(f"✗ File not found: {fp}", file=sys.stderr)
            fail += 1
            continue
        print(f"[{os.path.basename(fp)}]")
        try:
            if sync_one_deck(api, fp, remote_decks, dry_run=args.dry_run):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            import traceback
            print(f"  ✗ Error: {e}", file=sys.stderr)
            print(f"  Traceback: {traceback.format_exc()}", file=sys.stderr)
            fail += 1
        print()

    print(f"Done: {ok} synced, {fail} failed")
    if args.dry_run:
        print("(dry run — nothing was changed)")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
