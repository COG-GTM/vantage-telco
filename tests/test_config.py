from __future__ import annotations

from app import db, security
from app.config import setting


def test_setting_reads_environment_value(monkeypatch):
    monkeypatch.setenv("EXAMPLE_SETTING", "value")
    monkeypatch.delenv("EXAMPLE_SETTING_FILE", raising=False)
    assert setting("EXAMPLE_SETTING") == "value"


def test_setting_file_wins_and_strips_trailing_newline(monkeypatch, tmp_path):
    path = tmp_path / "secret"
    path.write_text("file-value\r\n", encoding="utf-8")
    monkeypatch.setenv("EXAMPLE_SETTING", "environment-value")
    monkeypatch.setenv("EXAMPLE_SETTING_FILE", str(path))
    assert setting("EXAMPLE_SETTING") == "file-value"


def test_setting_uses_default_when_unconfigured(monkeypatch):
    monkeypatch.delenv("EXAMPLE_SETTING", raising=False)
    monkeypatch.delenv("EXAMPLE_SETTING_FILE", raising=False)
    assert setting("EXAMPLE_SETTING", "default") == "default"


def test_setting_preserves_empty_environment_value(monkeypatch):
    monkeypatch.delenv("EXAMPLE_SETTING_FILE", raising=False)
    monkeypatch.setenv("EXAMPLE_SETTING", "")
    assert setting("EXAMPLE_SETTING", "default") == ""


def test_mongo_uri_reads_secret_file(monkeypatch, tmp_path):
    path = tmp_path / "mongo-uri"
    path.write_text("mongodb://file:27017\n", encoding="utf-8")
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setenv("MONGO_URI_FILE", str(path))
    assert db.mongo_uri() == "mongodb://file:27017"


def test_auth_settings_reads_dev_secret_file(monkeypatch, tmp_path):
    path = tmp_path / "dev-secret"
    path.write_text("file-dev-secret\n", encoding="utf-8")
    monkeypatch.delenv("VANTAGE_AUTH_DEV_SECRET", raising=False)
    monkeypatch.setenv("VANTAGE_AUTH_DEV_SECRET_FILE", str(path))
    security.reset_settings_cache()
    try:
        assert security.AuthSettings.from_env().dev_secret == "file-dev-secret"
    finally:
        security.reset_settings_cache()
