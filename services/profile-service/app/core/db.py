from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


DATABASE_URL_FILE = Path("/var/run/secrets/nexus/DATABASE_URL")


def database_url() -> str | None:
    if DATABASE_URL_FILE.is_file():
        return DATABASE_URL_FILE.read_text().strip()
    return settings.DATABASE_URL


@contextmanager
def db_cursor() -> Generator:
    url = database_url()
    if not url or psycopg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    with psycopg.connect(
        url,
        row_factory=dict_row,
        connect_timeout=settings.DB_CONNECT_TIMEOUT_SECONDS,
    ) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


def init_schema() -> None:
    if not database_url() or psycopg is None:
        return
    with db_cursor() as cur:
        cur.execute(
            """
            create table if not exists profiles (
              user_id uuid primary key,
              email text unique not null,
              display_name text not null,
              avatar_url text,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )
