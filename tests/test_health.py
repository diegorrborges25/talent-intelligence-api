"""Testes de metadados/health e documentação."""


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["docs"] == "/docs"


def test_health_public(client):
    """Health não exige autenticação e reporta contagens do seed."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["role_nodes"] == 10
    assert body["salary_observations"] > 100
    assert body["llm_enabled"] is False


def test_openapi_available(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/v1/parse-resume" in resp.json()["paths"]


def test_taxonomy_listing(client):
    resp = client.get("/api/v1/taxonomy")
    assert resp.status_code == 200
    assert len(resp.json()) == 10
    assert all(">" in node["path"] for node in resp.json())
