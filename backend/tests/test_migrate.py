from sqlalchemy import create_engine, inspect

from core.config import settings
from database.migrate import run_migrations


def test_run_migrations_creates_all_tables_on_a_fresh_database(tmp_path, monkeypatch):
    db_file = tmp_path / "fresh.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file.as_posix()}")

    run_migrations()

    tables = set(inspect(create_engine(settings.DATABASE_URL)).get_table_names())
    assert {"users", "patients", "reports", "medical_documents"} <= tables


def test_run_migrations_is_safe_to_repeat(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings, "DATABASE_URL", f"sqlite:///{(tmp_path / 'again.db').as_posix()}"
    )

    run_migrations()
    run_migrations()
