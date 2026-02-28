"""Melora configuration checker.

Validates environment variables, Matrix connectivity, and database access.
Run with: python -m app --check
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

_PASS = "\033[32m✓\033[0m"
_FAIL = "\033[31m✗\033[0m"
_failures = 0


def _ok(msg: str) -> None:
    print(f"  [{_PASS}] {msg}")


def _fail(msg: str) -> None:
    global _failures
    _failures += 1
    print(f"  [{_FAIL}] {msg}")


def _hint(msg: str) -> None:
    print(f"        {msg}")


def _section(title: str) -> None:
    print(f"\n{title}")
    print("─" * len(title))


# ── Environment variables ────────────────────────────────────────────

def _check_env() -> dict[str, str]:
    """Validate required env vars and return their values."""
    _section("Environment variables")

    required = [
        "MATRIX_HOMESERVER_URL",
        "MATRIX_BOT_USER_ID",
        "MATRIX_BOT_ACCESS_TOKEN",
        "MATRIX_ARRIVALS_ROOM_ID",
        "WEBHOOK_SECRET",
    ]
    vals: dict[str, str] = {}
    for var in required:
        raw = os.environ.get(var, "").strip()
        if raw:
            if "TOKEN" in var or "SECRET" in var:
                shown = raw[:4] + "····" + raw[-4:] if len(raw) > 12 else "····"
            else:
                shown = raw
            _ok(f"{var} = {shown}")
            vals[var] = raw
        else:
            _fail(f"{var} is missing or empty")

    db = os.environ.get("DATABASE_PATH", "").strip()
    if db:
        _ok(f"DATABASE_PATH = {db}")
        vals["DATABASE_PATH"] = db
    else:
        _ok("DATABASE_PATH = melora.db (default)")
        vals["DATABASE_PATH"] = "melora.db"

    return vals


# ── Matrix connectivity ──────────────────────────────────────────────

async def _check_matrix(vals: dict[str, str]) -> None:
    """Verify homeserver reachability, token validity, and room membership."""
    _section("Matrix connectivity")

    hs = vals.get("MATRIX_HOMESERVER_URL")
    uid = vals.get("MATRIX_BOT_USER_ID")
    token = vals.get("MATRIX_BOT_ACCESS_TOKEN")
    room = vals.get("MATRIX_ARRIVALS_ROOM_ID")

    if not all([hs, uid, token, room]):
        _fail("Skipping — required environment variables are missing")
        return

    from nio import AsyncClient, AsyncClientConfig, JoinedRoomsResponse

    cfg = AsyncClientConfig(max_timeouts=0, request_timeout=10)
    client = AsyncClient(hs, uid, config=cfg)
    client.access_token = token

    try:
        resp = await client.joined_rooms()
    except Exception as exc:
        _fail(f"Cannot reach homeserver at {hs}")
        _hint(f"Error: {exc}")
        _hint("Check the URL, port, and that the server is running.")
        return
    finally:
        await client.close()

    if isinstance(resp, JoinedRoomsResponse):
        _ok(f"Homeserver is reachable ({hs})")
        _ok(f"Bot access token is valid ({uid})")
        if room in resp.rooms:
            _ok(f"Bot is a member of room {room}")
        else:
            _fail(f"Bot is NOT a member of room {room}")
            _hint("Invite the bot to the room, or verify MATRIX_ARRIVALS_ROOM_ID.")
    else:
        status = getattr(resp, "status_code", None)
        message = getattr(resp, "message", str(resp))
        _ok(f"Homeserver is reachable ({hs})")
        if str(status) in ("401", "M_UNKNOWN_TOKEN"):
            _fail("Bot access token is invalid (401 Unauthorized)")
            _hint("Generate a new token or check MATRIX_BOT_ACCESS_TOKEN.")
        else:
            _fail(f"Matrix API error — {message}")


# ── Database ─────────────────────────────────────────────────────────

async def _check_database(vals: dict[str, str]) -> None:
    """Verify the database path is usable."""
    _section("Database")

    db_path = Path(vals.get("DATABASE_PATH", "melora.db"))
    parent = db_path.parent.resolve()

    if db_path.exists():
        import aiosqlite

        try:
            async with aiosqlite.connect(str(db_path)) as conn:
                cur = await conn.execute("PRAGMA integrity_check")
                row = await cur.fetchone()
                if row and row[0] == "ok":
                    _ok(f"Database exists and passes integrity check ({db_path})")
                else:
                    _fail(f"Database integrity check failed ({db_path})")
        except Exception as exc:
            _fail(f"Cannot open database at {db_path} — {exc}")
    elif parent.exists() and os.access(str(parent), os.W_OK):
        _ok(f"Database will be created at {db_path} (directory is writable)")
    else:
        _fail(f"Cannot write to database directory ({parent})")


# ── Entry point ──────────────────────────────────────────────────────

async def _run_async(vals: dict[str, str]) -> None:
    await _check_matrix(vals)
    await _check_database(vals)


def run_checks() -> int:
    """Run all configuration checks. Returns 0 on success, 1 on failure."""
    global _failures
    _failures = 0

    print("\nMelora configuration check")
    print("══════════════════════════")

    load_dotenv()
    vals = _check_env()
    asyncio.run(_run_async(vals))

    print()
    if _failures:
        print(f"  {_failures} check(s) failed.\n")
        return 1
    print("  All checks passed!\n")
    return 0
