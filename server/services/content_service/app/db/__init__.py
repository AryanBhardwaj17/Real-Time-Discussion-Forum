"""Content service database session management."""

from collections.abc import AsyncGenerator

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.base import Base
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL, echo=settings.DEBUG,
    pool_size=10, max_overflow=5, pool_recycle=3600, pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
)


def _run_alembic_upgrade() -> None:
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def _stamp_if_needed(has_alembic: bool, has_tables: bool) -> None:
    if has_alembic or not has_tables:
        return
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")


async def _pre_migration_fixups() -> None:
    """One-time fixups for legacy schemas predating Alembic."""
    async with engine.begin() as conn:
        # Migrate legacy ENUM columns to VARCHAR
        for col, new_type, table in [
            ("target_type", "VARCHAR(20)", "reports"),
            ("reason", "VARCHAR(30)", "reports"),
            ("status", "VARCHAR(20)", "reports"),
        ]:
            await conn.execute(sqlalchemy.text(f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = '{table}' AND column_name = '{col}'
                        AND data_type = 'USER-DEFINED'
                    ) THEN
                        ALTER TABLE {table} ALTER COLUMN {col} DROP DEFAULT;
                        ALTER TABLE {table} ALTER COLUMN {col} TYPE {new_type} USING {col}::text;
                    END IF;
                END $$;
            """))
        for enum_name in ("reporttargettype", "reportreason", "reportstatus"):
            await conn.execute(sqlalchemy.text(f"DROP TYPE IF EXISTS {enum_name}"))

        # Drop legacy columns replaced by hybrid_property / junction table / Meilisearch
        for col, table in [
            ("tags", "threads"),
            ("is_pinned", "threads"),
            ("is_locked", "threads"),
            ("is_edited", "threads"),
            ("search_vector", "threads"),
            ("is_edited", "comments"),
        ]:
            await conn.execute(sqlalchemy.text(f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = '{table}' AND column_name = '{col}'
                    ) THEN
                        ALTER TABLE {table} DROP COLUMN {col};
                    END IF;
                END $$;
            """))

        # Add FK constraints on reports if missing
        for fk_name, col, ref_table in [
            ("reports_reason_fkey", "reason", "report_reasons(code)"),
            ("reports_status_fkey", "status", "report_statuses(code)"),
        ]:
            await conn.execute(sqlalchemy.text(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE constraint_name = '{fk_name}'
                    ) THEN
                        ALTER TABLE reports
                            ADD CONSTRAINT {fk_name}
                            FOREIGN KEY ({col}) REFERENCES {ref_table};
                    END IF;
                END $$;
            """))

        # Add author_role if missing
        await conn.execute(sqlalchemy.text(
            "ALTER TABLE threads ADD COLUMN IF NOT EXISTS author_role VARCHAR(20) NOT NULL DEFAULT 'member'"
        ))
        await conn.execute(sqlalchemy.text(
            "ALTER TABLE comments ADD COLUMN IF NOT EXISTS author_role VARCHAR(20) NOT NULL DEFAULT 'member'"
        ))


async def _stamp_existing_db() -> None:
    import asyncio
    async with engine.connect() as conn:
        result = await conn.execute(sqlalchemy.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
        ))
        has_alembic = result.scalar()

        result = await conn.execute(sqlalchemy.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'threads')"
        ))
        has_tables = result.scalar()

    await asyncio.to_thread(_stamp_if_needed, has_alembic, has_tables)


async def create_tables() -> None:
    import asyncio
    from app import models  # noqa: F401

    await _pre_migration_fixups()
    await _stamp_existing_db()
    await asyncio.to_thread(_run_alembic_upgrade)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
