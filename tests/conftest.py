import os

os.environ.setdefault("VANTAGE_AUTH_DEV_SECRET", "test-secret")
os.environ.setdefault("VANTAGE_RATE_LIMIT_PER_MINUTE", "0")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import (
    SCOPE_BILLING_OPS,
    SCOPE_NOC,
    SCOPE_SALES_ENGINEERING,
    mint_token,
    rate_limiter,
)


@pytest.fixture
def app_client():
    return TestClient(app)


@pytest.fixture
def token_for():
    def factory(scopes):
        return mint_token("test-user", scopes)

    return factory


@pytest.fixture
def client(token_for):
    token = token_for([SCOPE_SALES_ENGINEERING, SCOPE_NOC, SCOPE_BILLING_OPS])
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def ops_client(token_for):
    token = token_for([SCOPE_NOC])
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def billing_ops_client(token_for):
    token = token_for([SCOPE_BILLING_OPS])
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def sales_client(token_for):
    token = token_for([SCOPE_SALES_ENGINEERING])
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    original = rate_limiter.limit_per_minute
    rate_limiter.reset()
    yield
    rate_limiter.limit_per_minute = original
    rate_limiter.reset()
