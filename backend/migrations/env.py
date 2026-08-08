from __future__ import annotations

from alembic import context
from sqlmodel import SQLModel

from src import models  # noqa: F401

config = context.config


def run_migrations_online() -> None:
    connectable = context.config.attributes.get("connection")
    if connectable is None:
        from sqlalchemy import engine_from_config, pool

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=SQLModel.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
