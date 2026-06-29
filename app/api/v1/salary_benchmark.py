"""Serviço de IA nº 2 — benchmark salarial e dispersão."""

import logging
import sqlite3

from fastapi import APIRouter, Depends

from ...ai.benchmark import benchmark
from ...logging_config import log_with_fields
from ...schemas import SalaryBenchmarkRequest, SalaryBenchmarkResponse
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("talent.api.salary_benchmark")
router = APIRouter(prefix="/salary-benchmark", tags=["IA · Benchmark Salarial"])


@router.post(
    "",
    response_model=SalaryBenchmarkResponse,
    summary="Benchmark salarial, dispersão e gap vs. oferta",
    dependencies=[Depends(rate_limit)],
)
def salary_benchmark(
    payload: SalaryBenchmarkRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Classifica o cargo, recupera observações comparáveis e calcula estatísticas
    (mediana, p25/p75, coeficiente de variação), outliers (IQR) e — se houver
    `offered_salary` — o gap frente à mediana de mercado.
    """
    result = benchmark(
        payload.description, db, region=payload.region,
        seniority=payload.seniority, offered_salary=payload.offered_salary,
    )
    log_with_fields(
        logger, logging.INFO, "salary_benchmark_done",
        user=user["username"], role=result.get("matched_role_path"),
        n=result.get("stats", {}).get("count") if result.get("stats") else 0,
    )
    return SalaryBenchmarkResponse(**result)
