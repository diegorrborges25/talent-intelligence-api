"""Endpoints de metadados: health-check e consulta da taxonomia de cargos."""

import sqlite3

from fastapi import APIRouter, Depends

from ... import __version__
from ...config import get_settings
from ...schemas import HealthResponse, RoleNode
from ..deps import get_db

router = APIRouter(tags=["Metadados"])


@router.get("/health", response_model=HealthResponse, summary="Status da aplicação")
def health(db: sqlite3.Connection = Depends(get_db)):
    """Endpoint público de saúde — não exige autenticação."""
    settings = get_settings()
    roles = db.execute("SELECT COUNT(*) AS n FROM role_taxonomy").fetchone()["n"]
    obs = db.execute("SELECT COUNT(*) AS n FROM salary_observation").fetchone()["n"]
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.app_env,
        llm_enabled=settings.llm_enabled,
        role_nodes=roles,
        salary_observations=obs,
    )


@router.get("/taxonomy", response_model=list[RoleNode], summary="Lista a taxonomia de cargos")
def list_taxonomy(db: sqlite3.Connection = Depends(get_db)):
    """Retorna todos os nós da taxonomia mestre de cargos carregada."""
    rows = db.execute(
        "SELECT role_id, area, track, specialization, canonical_label "
        "FROM role_taxonomy ORDER BY area, track"
    ).fetchall()
    nodes = []
    for r in rows:
        parts = [r["area"], r["track"]] + ([r["specialization"]] if r["specialization"] else [])
        nodes.append(
            RoleNode(
                role_id=r["role_id"],
                area=r["area"],
                track=r["track"],
                specialization=r["specialization"],
                canonical_label=r["canonical_label"],
                path=" > ".join(p.upper() for p in parts),
            )
        )
    return nodes
