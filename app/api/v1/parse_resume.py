"""Serviço de IA nº 1 — parse/classificação de currículos e perfis."""

import logging
import sqlite3

from fastapi import APIRouter, Depends

from ...ai.classifier import classify
from ...logging_config import log_with_fields
from ...schemas import ParseResumeRequest, ParseResumeResponse
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("talent.api.parse_resume")
router = APIRouter(prefix="/parse-resume", tags=["IA · Parse de Currículo"])


@router.post(
    "",
    response_model=ParseResumeResponse,
    summary="Estrutura e classifica um currículo/perfil em texto livre",
    dependencies=[Depends(rate_limit)],
)
def parse_resume(
    payload: ParseResumeRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Transforma um texto livre de currículo em perfil estruturado + cargo taxonômico.

    Pipeline híbrido: **regras determinísticas → similaridade contra a taxonomia →
    (opcional) refino por LLM**. Retorna cargo canônico, skills, senioridade,
    formação, candidatos, decisão (MATCH/REVIEW/NO_MATCH), confiança e evidências.
    """
    result = classify(payload.text, db)
    log_with_fields(
        logger, logging.INFO, "parse_resume_done",
        user=user["username"], decision=result["decision"],
        confidence=result["confidence"], engine=result["engine"],
    )
    return ParseResumeResponse(**result)
