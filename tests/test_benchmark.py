"""Testes do Serviço de IA nº 2 (benchmark salarial) e nº 3 (match)."""


def test_benchmark_returns_stats(client, auth_headers):
    resp = client.post(
        "/api/v1/salary-benchmark",
        json={"description": "cientista de dados machine learning", "seniority": "Júnior"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_role_path"] is not None
    stats = body["stats"]
    assert stats["count"] >= 3
    assert stats["min"] <= stats["median"] <= stats["max"]
    assert stats["p25"] <= stats["p75"]
    assert body["dispersion_level"] in ("baixa", "media", "alta")
    # Há um outlier proposital de cientista de dados júnior no seed.
    assert len(body["outliers"]) >= 1


def test_benchmark_offer_assessment(client, auth_headers):
    resp = client.post(
        "/api/v1/salary-benchmark",
        json={
            "description": "analista de dados bi power bi sql",
            "seniority": "Pleno",
            "offered_salary": 20000,
        },
        headers=auth_headers,
    )
    body = resp.json()
    offer = body["offer_assessment"]
    assert offer is not None
    # 20000 deve estar bem acima da mediana de um BI Pleno (~8000).
    assert offer["gap_abs"] > 0
    assert offer["market_median"] < 20000


def test_benchmark_region_filter(client, auth_headers):
    resp = client.post(
        "/api/v1/salary-benchmark",
        json={"description": "engenheiro de software backend python", "region": "Sudeste"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "região" in resp.json()["comparable_basis"]


def test_benchmark_unmatched_item(client, auth_headers):
    resp = client.post(
        "/api/v1/salary-benchmark",
        json={"description": "xpto zzz qwerty nada"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # Sem cargo comparável -> sem stats, com nota explicativa.
    assert resp.json()["stats"] is None
    assert resp.json()["note"] is not None


def test_match_strong_fit(client, auth_headers):
    resp = client.post(
        "/api/v1/match",
        json={
            "resume": "Desenvolvedor backend sênior com 8 anos em Python, FastAPI, Docker, AWS e PostgreSQL. Inglês.",
            "job": "Vaga backend sênior: Python, FastAPI, Docker, AWS. 5+ anos.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["same_track"] is True
    assert body["decision"] == "FIT"
    assert body["skill_match"] >= 0.6


def test_match_seniority_gap_review(client, auth_headers):
    resp = client.post(
        "/api/v1/match",
        json={
            "resume": "Desenvolvedor backend júnior com 1 ano em Python e FastAPI.",
            "job": "Backend sênior: Python, FastAPI. 6+ anos.",
        },
        headers=auth_headers,
    )
    body = resp.json()
    assert body["same_track"] is True
    assert body["decision"] == "REVIEW"
    # Senioridade/experiência abaixo do exigido -> lacunas críticas registradas.
    assert len(body["critical_gaps"]) >= 1


def test_match_no_fit_different_track(client, auth_headers):
    resp = client.post(
        "/api/v1/match",
        json={
            "resume": "Desenvolvedor backend com 5 anos em Python, FastAPI e Docker.",
            "job": "Designer de produto UX/UI com Figma e Sketch.",
        },
        headers=auth_headers,
    )
    body = resp.json()
    assert body["same_track"] is False
    assert body["decision"] == "NO_FIT"


def test_match_missing_skills_review(client, auth_headers):
    resp = client.post(
        "/api/v1/match",
        json={
            "resume": "Backend pleno com 4 anos em Python.",
            "job": "Vaga backend: Python, FastAPI, Kubernetes, Kafka. 3+ anos.",
        },
        headers=auth_headers,
    )
    body = resp.json()
    assert body["same_track"] is True
    assert body["decision"] == "REVIEW"
    assert len(body["missing_skills"]) >= 1
