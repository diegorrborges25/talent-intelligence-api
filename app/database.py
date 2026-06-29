"""Camada de dados em SQLite (stdlib `sqlite3`).

Escolha deliberada: SQLite não exige servidor nem dependência externa, então a API
roda em qualquer máquina (critério de avaliação: "executa em outro computador").
O esquema é um recorte enxuto do modelo de inteligência de talentos (taxonomia de
cargos + observações salariais), suficiente para alimentar os serviços de IA e o benchmark.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("talent.database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'recruiter'
);

-- Taxonomia mestre de cargos (hierarquia área > trilha > especialização).
CREATE TABLE IF NOT EXISTS role_taxonomy (
    role_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    area            TEXT NOT NULL,
    track           TEXT NOT NULL,
    specialization  TEXT,
    canonical_label TEXT NOT NULL,
    keywords        TEXT NOT NULL,   -- skills/sinônimos separados por vírgula
    default_currency TEXT DEFAULT 'BRL'
);

-- Observações salariais normalizadas (base do benchmark).
CREATE TABLE IF NOT EXISTS salary_observation (
    obs_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id         INTEGER NOT NULL REFERENCES role_taxonomy(role_id),
    canonical_name  TEXT NOT NULL,
    company         TEXT NOT NULL,
    source          TEXT,
    region          TEXT NOT NULL,
    seniority       TEXT NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'BRL',
    monthly_salary  REAL NOT NULL,
    observation_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_salary_role      ON salary_observation(role_id);
CREATE INDEX IF NOT EXISTS idx_salary_region    ON salary_observation(region);
CREATE INDEX IF NOT EXISTS idx_salary_seniority ON salary_observation(seniority);
"""


def get_db_path() -> str:
    from .config import get_settings

    return get_settings().database_path


def connect() -> sqlite3.Connection:
    """Abre uma conexão com row factory de dicionário e FKs habilitadas."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Cria o esquema (idempotente) e popula com seed caso esteja vazio."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) AS n FROM role_taxonomy").fetchone()["n"]
        if count == 0:
            from data.seed_talent import seed_database

            seed_database(conn)
            logger.info("Banco populado com dados de seed (cargos + salários).")
        else:
            logger.info("Banco já populado (%s nós de taxonomia).", count)
    finally:
        conn.close()


def reset_db() -> None:
    """Remove o arquivo do banco (usado em testes)."""
    p = Path(get_db_path())
    if p.exists():
        p.unlink()
