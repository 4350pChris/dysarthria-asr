from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlmodel import Session, create_engine

from .paths import DB_FILE


def database_url(db_file: Path = DB_FILE) -> str:
    return f"sqlite:///{db_file}"


def create_database_engine(db_file: Path = DB_FILE):
    db_file.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url(db_file), connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys = ON")

    return engine


engine = create_database_engine()


def get_session() -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:
        yield session


def commit(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def run_migrations(db_file: Path = DB_FILE) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url(db_file))
    command.upgrade(config, "head")


def init_db() -> None:
    """Upgrade the local database, then add missing built-in seed data."""
    global engine
    run_migrations(DB_FILE)
    engine.dispose()
    engine = create_database_engine(DB_FILE)
    from .seed import seed_database

    with Session(engine) as session:
        seed_database(session)
        session.commit()
