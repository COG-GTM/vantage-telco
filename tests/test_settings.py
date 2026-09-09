from __future__ import annotations

from pathlib import Path

import pytest

from app import db, security
from app.settings import get_setting


def test_missing_setting_is_none(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VANTAGE_TEST_SETTING", raising=False)
    monkeypatch.delenv("VANTAGE_TEST_SETTING_FILE", raising=False)
    assert get_setting("VANTAGE_TEST_SETTING") is None


def test_plain_env_var_is_used(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VANTAGE_TEST_SETTING_FILE", raising=False)
    monkeypatch.setenv("VANTAGE_TEST_SETTING", "from-env")
    assert get_setting("VANTAGE_TEST_SETTING") == "from-env"


def test_empty_env_var_is_none(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VANTAGE_TEST_SETTING_FILE", raising=False)
    monkeypatch.setenv("VANTAGE_TEST_SETTING", "")
    assert get_setting("VANTAGE_TEST_SETTING") is None


def test_file_wins_over_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    secret = tmp_path / "mongo_uri"
    secret.write_text("mongodb://from-file/\n")
    monkeypatch.setenv("VANTAGE_TEST_SETTING", "from-env")
    monkeypatch.setenv("VANTAGE_TEST_SETTING_FILE", str(secret))
    assert get_setting("VANTAGE_TEST_SETTING") == "mongodb://from-file/"


def test_file_value_is_stripped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    secret = tmp_path / "secret"
    secret.write_text("  s3cret \r\n")
    monkeypatch.delenv("VANTAGE_TEST_SETTING", raising=False)
    monkeypatch.setenv("VANTAGE_TEST_SETTING_FILE", str(secret))
    assert get_setting("VANTAGE_TEST_SETTING") == "s3cret"


def test_empty_file_falls_back_to_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    secret = tmp_path / "empty"
    secret.write_text("\n")
    monkeypatch.setenv("VANTAGE_TEST_SETTING", "from-env")
    monkeypatch.setenv("VANTAGE_TEST_SETTING_FILE", str(secret))
    assert get_setting("VANTAGE_TEST_SETTING") == "from-env"


def test_empty_file_without_env_is_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    secret = tmp_path / "empty"
    secret.write_text("")
    monkeypatch.delenv("VANTAGE_TEST_SETTING", raising=False)
    monkeypatch.setenv("VANTAGE_TEST_SETTING_FILE", str(secret))
    assert get_setting("VANTAGE_TEST_SETTING") is None


def test_missing_file_falls_back_to_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANTAGE_TEST_SETTING", "from-env")
    monkeypatch.setenv("VANTAGE_TEST_SETTING_FILE", str(tmp_path / "does-not-exist"))
    assert get_setting("VANTAGE_TEST_SETTING") == "from-env"


def test_db_reads_mongo_settings_from_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "mongo_uri").write_text("mongodb://file-host/\n")
    (tmp_path / "mongo_db").write_text("vantage_file\n")
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.delenv("MONGO_DB", raising=False)
    monkeypatch.setenv("MONGO_URI_FILE", str(tmp_path / "mongo_uri"))
    monkeypatch.setenv("MONGO_DB_FILE", str(tmp_path / "mongo_db"))
    assert db.mongo_enabled()
    assert db.mongo_uri() == "mongodb://file-host/"
    assert db.mongo_db_name() == "vantage_file"


def test_db_name_defaults_to_vantage(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MONGO_DB", raising=False)
    monkeypatch.delenv("MONGO_DB_FILE", raising=False)
    assert db.mongo_db_name() == "vantage"


def test_auth_secret_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "auth").write_text("file-secret\n")
    monkeypatch.delenv("VANTAGE_AUTH_DEV_SECRET", raising=False)
    monkeypatch.setenv("VANTAGE_AUTH_DEV_SECRET_FILE", str(tmp_path / "auth"))
    token = security.mint_token("alice", [security.SCOPE_NOC])
    assert security.verify_token(token).sub == "alice"
    assert security.verify_token(token, secret="file-secret").sub == "alice"
