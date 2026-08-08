from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from . import database
from .paths import STATIC_DIR, TATOEBA_PROMPTS_FILE
from .routers import labeling, phrases, training, transcription
from .tatoeba import ensure_prompts
from .training_prompts import import_prompts


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level)
    logging.getLogger("src").setLevel(level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    try:
        ensure_prompts(TATOEBA_PROMPTS_FILE)
        with Session(database.engine) as session:
            imported = import_prompts(TATOEBA_PROMPTS_FILE, session)
        if imported:
            logging.getLogger("src").info(
                "Imported %s Tatoeba prompts.", imported)
    except Exception:
        logging.getLogger("src").warning(
            "Tatoeba prompt setup failed; continuing without it.", exc_info=True)
    yield


def create_app() -> FastAPI:
    configure_logging()
    database.init_db()

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
