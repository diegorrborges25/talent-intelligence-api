"""Benchmark salarial, dispersão e detecção de outliers (Serviço de IA nº 2).

Diferente do Serviço 1 (NLP/classificação), aqui a "inteligência" é analítica:
  - classifica a descrição para achar o cargo comparável na taxonomia;
  - recupera as observações salariais desse grupo (filtrando região/senioridade);
  - calcula estatísticas (mediana, p25/p75, desvio, coeficiente de variação);
  - sinaliza outliers pelo método do IQR (intervalo interquartil);
  - quantifica o gap da oferta vs. a mediana de mercado.
"""

import sqlite3
import statistics
from collections import defaultdict

from .classifier import classify


def _quantile(sorted_vals: list[float], q: float) -> float:
    """Quantil por interpolação linear (robusto p/ amostras pequenas)."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < len(sorted_vals):
        return sorted_vals[lo] + frac * (sorted_vals[lo + 1] - sorted_vals[lo])
    return sorted_vals[lo]


def _dispersion_level(cv: float) -> str:
    if cv < 0.15:
        return "baixa"
    if cv < 0.35:
        return "media"
    return "alta"


def benchmark(
    description: str,
    conn: sqlite3.Connection,
    region: str | None = None,
    seniority: str | None = None,
    offered_salary: float | None = None,
) -> dict:
    """Executa o benchmark e devolve dict pronto p/ SalaryBenchmarkResponse."""
    cls = classify(description, conn, use_llm=False)
    role_id = cls.get("role_id")
    path = cls.get("role_path")

    basis_parts = ["cargo (trilha/especialização)"]
    if region:
        basis_parts.append("região")
    if seniority:
        basis_parts.append("senioridade")

    base = {
        "raw_description": description,
        "matched_role_path": path,
        "classification_confidence": cls["confidence"],
        "comparable_basis": " + ".join(basis_parts),
        "currency": "BRL",
    }

    if not role_id:
        base["note"] = (
            "Não foi possível associar a descrição a um cargo comparável da taxonomia. "
            "Refine a descrição ou cadastre o cargo na taxonomia mestre."
        )
        return base

    query = (
        "SELECT company, source, region, seniority, monthly_salary "
        "FROM salary_observation WHERE role_id = ?"
    )
    params: list = [role_id]
    if region:
        query += " AND region = ?"
        params.append(region)
    if seniority:
        query += " AND seniority = ?"
        params.append(seniority)
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]

    if len(rows) < 3:
        base["note"] = (
            f"Amostra insuficiente para benchmark confiável "
            f"({len(rows)} observação(ões)). Mínimo recomendado: 3."
        )
        return base

    salaries = sorted(r["monthly_salary"] for r in rows)
    median = statistics.median(salaries)
    mean = statistics.fmean(salaries)
    std = statistics.pstdev(salaries)
    p25, p75 = _quantile(salaries, 0.25), _quantile(salaries, 0.75)
    cv = round(std / mean, 4) if mean else 0.0

    base["stats"] = {
        "count": len(salaries),
        "median": round(median, 2),
        "mean": round(mean, 2),
        "p25": round(p25, 2),
        "p75": round(p75, 2),
        "min": round(salaries[0], 2),
        "max": round(salaries[-1], 2),
        "std": round(std, 2),
        "coefficient_of_variation": cv,
    }
    base["dispersion_level"] = _dispersion_level(cv)

    # Outliers pelo método IQR (1.5 * intervalo interquartil).
    iqr = p75 - p25
    lo_fence, hi_fence = p25 - 1.5 * iqr, p75 + 1.5 * iqr
    outliers = []
    for r in rows:
        salary = r["monthly_salary"]
        if salary > hi_fence:
            outliers.append({**r, "reason": "acima do limite superior (IQR)"})
        elif salary < lo_fence:
            outliers.append({**r, "reason": "abaixo do limite inferior (IQR)"})
    base["outliers"] = [
        {
            "company": o["company"],
            "region": o["region"],
            "seniority": o["seniority"],
            "monthly_salary": round(o["monthly_salary"], 2),
            "reason": o["reason"],
        }
        for o in sorted(outliers, key=lambda x: x["monthly_salary"], reverse=True)
    ]

    # Agrupamentos por empresa, região e senioridade (mediana de cada grupo).
    def _group(field: str) -> list[dict]:
        buckets: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            buckets[r[field]].append(r["monthly_salary"])
        return sorted(
            (
                {"key": k, "count": len(v), "median_salary": round(statistics.median(v), 2)}
                for k, v in buckets.items()
            ),
            key=lambda x: x["median_salary"],
        )

    base["by_company"] = _group("company")
    base["by_region"] = _group("region")
    base["by_seniority"] = _group("seniority")

    # Gap da oferta vs. mediana de mercado.
    if offered_salary:
        gap_abs = offered_salary - median
        gap_pct = round((gap_abs / median) * 100, 2) if median else 0.0
        if gap_abs < -0.01:
            verdict = (
                f"Oferta {abs(gap_pct):.1f}% abaixo da mediana de mercado — "
                f"risco de baixa competitividade/atração."
            )
        elif gap_abs > 0.01:
            verdict = (
                f"Oferta {gap_pct:.1f}% acima da mediana de mercado — "
                f"competitiva, avaliar custo."
            )
        else:
            verdict = "Oferta alinhada à mediana de mercado."
        base["offer_assessment"] = {
            "offered_salary": round(offered_salary, 2),
            "market_median": round(median, 2),
            "gap_abs": round(gap_abs, 2),
            "gap_pct": gap_pct,
            "verdict": verdict,
        }

    return base
