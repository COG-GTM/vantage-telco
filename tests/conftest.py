from __future__ import annotations

import os

os.environ.setdefault("VANTAGE_AUTH_DEV_SECRET", "test-secret-not-for-prod")
os.environ.setdefault("VANTAGE_RATE_LIMIT_PER_MINUTE", "100000")

import pytest
from fastapi.testclient import TestClient

from app import security

security.reset_settings_cache()

from app.main import app  # noqa: E402


def mint(scopes, **kw) -> str:
    return security.mint_dev_token(scopes, **kw)


@pytest.fixture
def token_for():
    def factory(scopes) -> dict[str, str]:
        return {"Authorization": f"Bearer {mint(scopes)}"}

    return factory


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {mint(security.ALL_SCOPES)}"})


@pytest.fixture(autouse=True)
def authenticate_module_clients(request):
    token = f"Bearer {mint(security.ALL_SCOPES)}"
    for value in vars(request.module).values():
        if isinstance(value, TestClient) and "Authorization" not in value.headers:
            value.headers["Authorization"] = token
