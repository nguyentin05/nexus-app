from pathlib import Path

from app.core import db


def test_database_url_prefers_mounted_secret(tmp_path: Path, monkeypatch) -> None:
    secret = tmp_path / "DATABASE_URL"
    secret.write_text("postgresql://rotated")
    monkeypatch.setattr(db, "DATABASE_URL_FILE", secret)
    assert db.database_url() == "postgresql://rotated"
