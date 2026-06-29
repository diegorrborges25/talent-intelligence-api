"""Schemas Pydantic — contratos de entrada e saída da API.

Requisito da disciplina: "Validação de dados". O Pydantic v2 valida tipos, limites
e formatos automaticamente; entradas inválidas resultam em HTTP 422 padronizado.
Cada modelo traz `examples`, que alimentam a documentação interativa (Swagger).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Autenticação
# --------------------------------------------------------------------------- #
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


# --------------------------------------------------------------------------- #
# Serviço 1 — Parse / classificação de currículo
# --------------------------------------------------------------------------- #
class ParseResumeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Texto livre de currículo ou trecho profissional.",
        examples=[
            "Engenheiro de software sênior com 8 anos de experiência em Python, "
            "Django, FastAPI, AWS e Docker. Mestrado em Ciência da Computação. "
            "Inglês avançado. Modelo remoto."
        ],
    )
    document_type: Optional[
        Literal["curriculo", "vaga", "perfil_linkedin", "desconhecido"]
    ] = Field(default="desconhecido", description="Tipo documental de origem (opcional).")


class EvidenceSpan(BaseModel):
    field: str
    text: str


class RoleCandidate(BaseModel):
    role_id: int
    path: str
    score: float = Field(..., ge=0, le=1)


class ParseResumeResponse(BaseModel):
    raw_text: str
    canonical_name: str
    area: Optional[str] = None
    track: Optional[str] = None
    specialization: Optional[str] = None
    role_id: Optional[int] = None
    role_path: Optional[str] = None
    seniority: Optional[str] = None
    years_experience: Optional[int] = None
    education_level: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    work_mode: Optional[str] = None
    decision: Literal["MATCH", "REVIEW", "NO_MATCH"]
    confidence: float = Field(..., ge=0, le=1)
    candidates: list[RoleCandidate] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    ambiguity_note: Optional[str] = None
    engine: str = Field(..., description="Motor usado: regras+similaridade [+llm].")


# --------------------------------------------------------------------------- #
# Serviço 2 — Benchmark salarial / dispersão
# --------------------------------------------------------------------------- #
class SalaryBenchmarkRequest(BaseModel):
    description: str = Field(
        ..., min_length=3, max_length=1000,
        examples=["engenheiro de software backend python"],
    )
    region: Optional[str] = Field(
        default=None, description="Filtra observações por região (ex.: 'Sudeste')."
    )
    seniority: Optional[
        Literal["Estágio", "Júnior", "Pleno", "Sênior", "Especialista"]
    ] = Field(default=None, description="Filtra observações por senioridade.")
    offered_salary: Optional[float] = Field(
        default=None, gt=0,
        description="Salário ofertado/praticado para calcular gap vs. mediana de mercado.",
    )


class SalaryStats(BaseModel):
    count: int
    median: float
    mean: float
    p25: float
    p75: float
    min: float
    max: float
    std: float
    coefficient_of_variation: float


class GroupStat(BaseModel):
    key: str
    count: int
    median_salary: float


class SalaryOutlier(BaseModel):
    company: str
    region: str
    seniority: str
    monthly_salary: float
    reason: str


class OfferAssessment(BaseModel):
    offered_salary: float
    market_median: float
    gap_abs: float
    gap_pct: float
    verdict: str


class SalaryBenchmarkResponse(BaseModel):
    raw_description: str
    matched_role_path: Optional[str] = None
    classification_confidence: float
    comparable_basis: str
    currency: str = "BRL"
    stats: Optional[SalaryStats] = None
    dispersion_level: Optional[Literal["baixa", "media", "alta"]] = None
    by_company: list[GroupStat] = Field(default_factory=list)
    by_region: list[GroupStat] = Field(default_factory=list)
    by_seniority: list[GroupStat] = Field(default_factory=list)
    outliers: list[SalaryOutlier] = Field(default_factory=list)
    offer_assessment: Optional[OfferAssessment] = None
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# Serviço 3 — Match candidato × vaga
# --------------------------------------------------------------------------- #
class MatchRequest(BaseModel):
    resume: str = Field(
        ..., min_length=3, max_length=4000,
        examples=["Desenvolvedor com 6 anos em Python, FastAPI, Docker e AWS. Inglês avançado."],
    )
    job: str = Field(
        ..., min_length=3, max_length=4000,
        examples=["Vaga sênior backend: Python, FastAPI, Kubernetes, AWS. 5+ anos. Inglês."],
    )


class MatchResponse(BaseModel):
    resume_role: str
    job_role: str
    same_track: bool
    role_resume: Optional[str] = None
    role_job: Optional[str] = None
    skill_match: float = Field(..., ge=0, le=1)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    decision: Literal["FIT", "REVIEW", "NO_FIT"]
    critical_gaps: list[str] = Field(default_factory=list)
    rationale: str
    confidence: float = Field(..., ge=0, le=1)


# --------------------------------------------------------------------------- #
# Metadados
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    llm_enabled: bool
    role_nodes: int
    salary_observations: int


class RoleNode(BaseModel):
    role_id: int
    area: str
    track: str
    specialization: Optional[str] = None
    canonical_label: str
    path: str
