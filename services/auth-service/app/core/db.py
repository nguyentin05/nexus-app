from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException, status

from app.core.config import settings

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - dependency is installed in runtime image
    psycopg = None
    dict_row = None


@contextmanager
def db_cursor() -> Generator:
    if not settings.DATABASE_URL or psycopg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    with psycopg.connect(
        settings.DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=settings.DB_CONNECT_TIMEOUT_SECONDS,
    ) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


def init_schema() -> None:
    if not settings.DATABASE_URL or psycopg is None:
        return
    with db_cursor() as cur:
        cur.execute(
            """
            create table if not exists users (
              id uuid primary key,
              email text unique not null,
              display_name text not null,
              password_hash text not null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )
