"""Fixtures de teste — banco isolado e cliente autenticado.

As variáveis de ambiente são definidas ANTES de importar o app, pois as settings
são cacheadas no import. Usamos um arquivo SQLite dedicado de teste, recriado a cada
sessão pelo lifespan do TestClient (que dispara o seed automaticamente).
"""

import os
from pathlib import Path

import pytest

# Configura ambiente de teste isolado.
os.environ["DATABASE_PATH"] = "test_talent.db"
os.environ["LOG_JSON"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["DEMO_USERNAME"] = "recruiter"
os.environ["DEMO_PASSWORD"] = "talent123"
os.environ["ANTHROPIC_API_KEY"] = ""  # garante execução offline nos testes
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import reset_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _clean_db():
    reset_db()
    yield
    p = Path("test_talent.db")
    if p.exists():
        p.unlink()


@pytest.fixture(scope="session")
def client():
    # O context manager dispara o lifespan (init_db + seed).
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "recruiter", "password": "talent123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
