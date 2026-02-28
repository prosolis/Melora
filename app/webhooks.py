import logging

from fastapi import APIRouter, Header, Request, Response

from app.config import config
from app.database import get_thread_root, is_event_posted, record_posted_event
from app.formatters import format_lidarr, format_radarr, format_sonarr
from app.matrix import post_to_thread

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook")

SOURCE_MAP = {
    "radarr": {"media_type": "movies", "formatter": format_radarr, "id_field": "movie"},
    "sonarr": {"media_type": "shows", "formatter": format_sonarr, "id_field": "series"},
    "lidarr": {"media_type": "music", "formatter": format_lidarr, "id_field": "artist"},
}


def _validate_secret(header_value: str | None) -> bool:
    return header_value == config.WEBHOOK_SECRET


def _extract_event_key(source: str, payload: dict) -> str | None:
    if source == "radarr":
        movie = payload.get("movie", {})
        movie_id = movie.get("id")
        if movie_id is not None:
            return f"radarr-{movie_id}"
    elif source == "sonarr":
        episodes = payload.get("episodes", [])
        if episodes:
            ep_id = episodes[0].get("id")
            if ep_id is not None:
                return f"sonarr-{ep_id}"
    elif source == "lidarr":
        album = payload.get("album", {})
        album_id = album.get("id")
        if album_id is not None:
            return f"lidarr-{album_id}"
    return None


def _extract_title(source: str, payload: dict) -> str:
    if source == "radarr":
        return payload.get("movie", {}).get("title", "Unknown")
    elif source == "sonarr":
        return payload.get("series", {}).get("title", "Unknown")
    elif source == "lidarr":
        return payload.get("artist", {}).get("name", "Unknown")
    return "Unknown"


async def _handle_webhook(source: str, payload: dict, secret: str | None) -> Response:
    if not _validate_secret(secret):
        return Response(status_code=401, content="Unauthorized")

    event_type = payload.get("eventType", "")
    if event_type != "Download":
        log.debug("Ignoring %s event from %s", event_type, source)
        return Response(status_code=200, content="OK")

    info = SOURCE_MAP[source]
    media_type = info["media_type"]
    formatter = info["formatter"]
    is_upgrade = payload.get("isUpgrade", False)

    event_key = _extract_event_key(source, payload)
    if event_key:
        if await is_event_posted(event_key):
            log.debug("Duplicate event %s, skipping", event_key)
            return Response(status_code=200, content="OK")

    try:
        plain, html = formatter(payload)
    except Exception:
        log.exception("Failed to format %s payload", source)
        return Response(status_code=200, content="OK")

    thread_root_id = await get_thread_root(media_type)
    if not thread_root_id:
        log.error("No thread root for %s — cannot post", media_type)
        return Response(status_code=200, content="OK")

    event_id = await post_to_thread(thread_root_id, plain, html)
    if event_id and event_key:
        title = _extract_title(source, payload)
        await record_posted_event(event_key, title, media_type, is_upgrade)

    return Response(status_code=200, content="OK")


@router.post("/radarr")
async def webhook_radarr(
    request: Request,
    x_arr_webhook_secret: str | None = Header(None),
):
    try:
        payload = await request.json()
    except Exception:
        log.exception("Failed to parse Radarr payload")
        return Response(status_code=200, content="OK")
    return await _handle_webhook("radarr", payload, x_arr_webhook_secret)


@router.post("/sonarr")
async def webhook_sonarr(
    request: Request,
    x_arr_webhook_secret: str | None = Header(None),
):
    try:
        payload = await request.json()
    except Exception:
        log.exception("Failed to parse Sonarr payload")
        return Response(status_code=200, content="OK")
    return await _handle_webhook("sonarr", payload, x_arr_webhook_secret)


@router.post("/lidarr")
async def webhook_lidarr(
    request: Request,
    x_arr_webhook_secret: str | None = Header(None),
):
    try:
        payload = await request.json()
    except Exception:
        log.exception("Failed to parse Lidarr payload")
        return Response(status_code=200, content="OK")
    return await _handle_webhook("lidarr", payload, x_arr_webhook_secret)
