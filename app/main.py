import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_db, get_thread_root, init_db, set_thread_root
from app.matrix import THREAD_ROOT_MESSAGES, close_client, send_thread_root
from app.webhooks import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Melora")
    await init_db()
    await _ensure_thread_roots()
    log.info("Melora ready")
    yield
    log.info("Shutting down Melora")
    await close_client()
    await close_db()


async def _ensure_thread_roots() -> None:
    for media_type in THREAD_ROOT_MESSAGES:
        existing = await get_thread_root(media_type)
        if existing:
            log.info("Thread root for %s: %s", media_type, existing)
            continue
        log.info("Creating thread root for %s", media_type)
        event_id = await send_thread_root(media_type)
        await set_thread_root(media_type, event_id)


app = FastAPI(title="Melora", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
