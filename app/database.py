import aiosqlite

from app.config import config

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _db


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(config.DATABASE_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute(
        """
        CREATE TABLE IF NOT EXISTS thread_roots (
            media_type TEXT PRIMARY KEY,
            event_id   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await _db.execute(
        """
        CREATE TABLE IF NOT EXISTS posted_events (
            id         TEXT PRIMARY KEY,
            title      TEXT NOT NULL,
            media_type TEXT NOT NULL,
            is_upgrade BOOLEAN NOT NULL,
            posted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await _db.commit()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def get_thread_root(media_type: str) -> str | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT event_id FROM thread_roots WHERE media_type = ?",
        (media_type,),
    )
    row = await cursor.fetchone()
    return row["event_id"] if row else None


async def set_thread_root(media_type: str, event_id: str) -> None:
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO thread_roots (media_type, event_id) VALUES (?, ?)",
        (media_type, event_id),
    )
    await db.commit()


async def is_event_posted(event_key: str) -> bool:
    db = await get_db()
    cursor = await db.execute(
        "SELECT 1 FROM posted_events WHERE id = ?",
        (event_key,),
    )
    return await cursor.fetchone() is not None


async def record_posted_event(
    event_key: str, title: str, media_type: str, is_upgrade: bool
) -> None:
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO posted_events (id, title, media_type, is_upgrade) VALUES (?, ?, ?, ?)",
        (event_key, title, media_type, is_upgrade),
    )
    await db.commit()
