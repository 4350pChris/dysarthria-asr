from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .paths import STATIC_DIR
from .routers import phrases, speech_attempts, transcription


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level)
    logging.getLogger("src").setLevel(level)


def create_app() -> FastAPI:
    configure_logging()
    init_db()

    app = FastAPI(title="Dysarthria ASR Prototype")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(transcription.router)
    app.include_router(speech_attempts.router)
    app.include_router(phrases.router)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
