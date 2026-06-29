"""Testes do Serviço de IA nº 1 — parse/classificação de currículos."""


def test_parse_backend_senior(client, auth_headers):
    text = ("Engenheiro de software sênior com 8 anos de experiência em Python, "
            "Django, FastAPI, AWS e Docker. Mestrado em Ciência da Computação. "
            "Inglês avançado. Modelo remoto.")
    resp = client.post("/api/v1/parse-resume", json={"text": text}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ("MATCH", "REVIEW")
    assert body["area"] == "Tecnologia"
    assert body["specialization"] == "Backend"
    # Extração determinística de atributos:
    assert body["seniority"] == "Sênior"
    assert body["years_experience"] == 8
    assert body["education_level"] == "Mestrado"
    assert "Python" in body["skills"]
    assert "FastAPI" in body["skills"]
    assert "Inglês" in body["languages"]
    assert body["work_mode"] == "remoto"
    assert 0 <= body["confidence"] <= 1
    assert len(body["candidates"]) > 0


def test_parse_data_scientist(client, auth_headers):
    resp = client.post(
        "/api/v1/parse-resume",
        json={"text": "Cientista de dados com Machine Learning, PyTorch, scikit-learn e Python. Doutorado."},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["area"] == "Dados"
    assert body["education_level"] == "Doutorado"
    assert "Machine Learning" in body["skills"]
    assert "PyTorch" in body["skills"]
    assert body["engine"].startswith("regras+similaridade")


def test_parse_gibberish_is_no_match_or_review(client, auth_headers):
    resp = client.post(
        "/api/v1/parse-resume",
        json={"text": "xpto zzz qwerty 123 nada disso"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] in ("NO_MATCH", "REVIEW")


def test_parse_validation_too_short(client, auth_headers):
    resp = client.post("/api/v1/parse-resume", json={"text": "ab"}, headers=auth_headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_parse_missing_field(client, auth_headers):
    resp = client.post("/api/v1/parse-resume", json={}, headers=auth_headers)
    assert resp.status_code == 422
