from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .paths import STATIC_DIR, TATOEBA_PROMPTS_FILE
from .routers import labeling, phrases, training, transcription
from .tatoeba import ensure_prompts


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level)
    logging.getLogger("src").setLevel(level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        count = ensure_prompts(TATOEBA_PROMPTS_FILE)
        logging.getLogger("src").info("Tatoeba prompt cache has %s prompts.", count)
    except Exception:
        logging.getLogger("src").warning("Tatoeba prompt download failed; continuing without it.", exc_info=True)
    yield


def create_app() -> FastAPI:
    configure_logging()
    init_db()

    app = FastAPI(title="Dysarthria ASR Prototype", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(transcription.router)
    app.include_router(labeling.router)
    app.include_router(phrases.router)
    app.include_router(training.router)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
