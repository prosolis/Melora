import logging

from fastapi import FastAPI

from app.database import close_db, get_thread_root, init_db, set_thread_root
from app.matrix import THREAD_ROOT_MESSAGES, close_client, send_thread_root, start_presence
from app.webhooks import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Melora")
app.include_router(webhook_router)


async def _ensure_thread_roots() -> None:
    for media_type in THREAD_ROOT_MESSAGES:
        existing = await get_thread_root(media_type)
        if existing:
            log.info("Thread root for %s: %s", media_type, existing)
            continue
        log.info("Creating thread root for %s", media_type)
        event_id = await send_thread_root(media_type)
        await set_thread_root(media_type, event_id)


@app.on_event("startup")
async def startup() -> None:
    log.info("Starting Melora")
    await init_db()
    await _ensure_thread_roots()
    await start_presence()
    log.info("Melora ready")


@app.on_event("shutdown")
async def shutdown() -> None:
    log.info("Shutting down Melora")
    await close_client()
    await close_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
