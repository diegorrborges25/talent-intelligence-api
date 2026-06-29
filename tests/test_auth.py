"""Testes de autenticação e segurança."""


def test_login_success(client):
    resp = client.post(
        "/api/v1/auth/token", data={"username": "recruiter", "password": "talent123"}
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    resp = client.post(
        "/api/v1/auth/token", data={"username": "recruiter", "password": "errada"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_error"


def test_protected_endpoint_requires_token(client):
    resp = client.post("/api/v1/parse-resume", json={"text": "engenheiro backend python"})
    assert resp.status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    resp = client.post(
        "/api/v1/parse-resume",
        json={"text": "engenheiro backend python"},
        headers={"Authorization": "Bearer token.invalido.aqui"},
    )
    assert resp.status_code == 401


def test_request_id_header_present(client):
    resp = client.get("/api/v1/health")
    assert "X-Request-ID" in resp.headers
