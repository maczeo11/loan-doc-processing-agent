import asyncio
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import pool, engine_from_config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from apps.api.config import settings
from apps.api.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Return database URL from CLI override, config, or settings."""
    cmd_url = context.get_x_argument(as_dictionary=True).get("url")
    if cmd_url:
        return cmd_url
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return ini_url
    url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    elif "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(url: str) -> None:
    """Run migrations using async engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    if "+asyncpg" in url or "+aiosqlite" in url:
        asyncio.run(run_async_migrations(url))
    else:
        # Synchronous engine for SQLite or standard postgresql driver
        configuration = config.get_section(config.config_ini_section) or {}
        configuration["sqlalchemy.url"] = url
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            do_run_migrations(connection)
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
