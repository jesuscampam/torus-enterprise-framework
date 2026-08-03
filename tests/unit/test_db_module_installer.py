"""Pruebas unitarias de backend/modules/database/installer.py (DatabaseInstaller)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.modules.database.installer import DatabaseInstaller


def test_head_revision_reads_versions_directory() -> None:
    installer = DatabaseInstaller(alembic_ini_path="alembic.ini")
    head = installer.head_revision()
    assert head is not None
    assert len(head) > 0


def test_upgrade_to_head_creates_alembic_version_table(tmp_path: Path) -> None:
    installer = DatabaseInstaller(alembic_ini_path="alembic.ini")
    db_path = tmp_path / "installer_test.db"

    installer.upgrade_to_head(f"sqlite+aiosqlite:///{db_path}")

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        connection.close()

    assert tables == {"alembic_version"}
    assert version is not None
    assert version[0] == installer.head_revision()


def test_upgrade_to_head_creates_no_business_tables(tmp_path: Path) -> None:
    """Solo infraestructura (Sprint 2.6): ninguna migración crea tablas de negocio."""
    installer = DatabaseInstaller(alembic_ini_path="alembic.ini")
    db_path = tmp_path / "no_business_tables.db"

    installer.upgrade_to_head(f"sqlite+aiosqlite:///{db_path}")

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert tables == {"alembic_version"}


def test_downgrade_removes_applied_revision(tmp_path: Path) -> None:
    installer = DatabaseInstaller(alembic_ini_path="alembic.ini")
    db_path = tmp_path / "downgrade_test.db"
    url = f"sqlite+aiosqlite:///{db_path}"

    installer.upgrade_to_head(url)
    installer.downgrade(url, "base")

    connection = sqlite3.connect(db_path)
    try:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        connection.close()

    assert version is None
