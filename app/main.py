"""Ponto de entrada da Talent Intelligence API (FastAPI).

Reúne: configuração, logging estruturado, inicialização do banco (lifespan),
middleware de correlação/acesso, tratadores de erro e o router versionado /api/v1.
Documentação interativa automática em /docs (Swagger) e /redoc.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.v1.router import api_router
from .config import get_settings
from .database import init_db
from .errors import register_exception_handlers
from .logging_config import configure_logging, log_with_fields, request_id_ctx

settings = get_settings()
configure_logging(level=settings.log_level, as_json=settings.log_json)
logger = logging.getLogger("talent.main")

DESCRIPTION = """
**Camada de Inteligência de Talentos** — estrutura, compara e precifica perfis profissionais.

Expõe serviços de IA sobre descrições livres de currículos e vagas:

* **Parse de currículo** — estrutura um texto livre em perfil + cargo taxonômico.
* **Benchmark salarial** — mediana, dispersão, outliers e gap vs. oferta.
* **Match candidato × vaga** — decide aderência (FIT/REVIEW/NO_FIT) por similaridade de skills.

Pipeline híbrido **regras + similaridade + (opcional) LLM**, com autenticação JWT,
versionamento, logs estruturados, tratamento de erros e validação de dados.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: cria/popula o banco automaticamente (roda em qualquer máquina).
    init_db()
    logger.info("startup_complete llm_enabled=%s", settings.llm_enabled)
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
    contact={"name": "Nexa Talent", "email": "contato@nexatalent.com"},
    license_info={"name": "MIT"},
)

register_exception_handlers(app)

# CORS liberado para facilitar demonstrações locais (Swagger, páginas HTML de demo,
# front-ends). Em produção, restrinja `allow_origins` aos domínios confiáveis.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Injeta request_id, mede latência e gera log de acesso estruturado."""
    rid = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    token = request_id_ctx.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = rid
    log_with_fields(
        logger, logging.INFO, "http_access",
        method=request.method, path=request.url.path,
        status=response.status_code, latency_ms=elapsed_ms,
    )
    return response


# Monta a v1 sob o prefixo versionado.
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Metadados"], summary="Raiz — informações da API")
def root():
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }
