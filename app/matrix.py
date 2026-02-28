import logging

from nio import AsyncClient, RoomSendResponse

from app.config import config

log = logging.getLogger(__name__)

_client: AsyncClient | None = None

THREAD_ROOT_MESSAGES: dict[str, str] = {
    "movies": "\U0001f3ac Movies",
    "shows": "\U0001f4fa Shows",
    "music": "\U0001f3b5 Music",
}


async def get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = AsyncClient(config.MATRIX_HOMESERVER_URL)
        _client.user_id = config.MATRIX_BOT_USER_ID
        _client.access_token = config.MATRIX_BOT_ACCESS_TOKEN
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def send_thread_root(media_type: str) -> str:
    client = await get_client()
    label = THREAD_ROOT_MESSAGES[media_type]
    content = {
        "msgtype": "m.text",
        "body": label,
    }
    resp = await client.room_send(
        config.MATRIX_ARRIVALS_ROOM_ID,
        "m.room.message",
        content,
    )
    if isinstance(resp, RoomSendResponse):
        log.info("Created thread root for %s: %s", media_type, resp.event_id)
        return resp.event_id
    raise RuntimeError(f"Failed to create thread root for {media_type}: {resp}")


async def post_to_thread(
    thread_root_event_id: str,
    plain_body: str,
    html_body: str,
) -> str | None:
    client = await get_client()
    content = {
        "msgtype": "m.text",
        "format": "org.matrix.custom.html",
        "body": plain_body,
        "formatted_body": html_body,
        "m.relates_to": {
            "rel_type": "m.thread",
            "event_id": thread_root_event_id,
        },
    }
    try:
        resp = await client.room_send(
            config.MATRIX_ARRIVALS_ROOM_ID,
            "m.room.message",
            content,
        )
        if isinstance(resp, RoomSendResponse):
            return resp.event_id
        log.error("Matrix send failed: %s", resp)
        return None
    except Exception:
        log.exception("Matrix posting error")
        return None
