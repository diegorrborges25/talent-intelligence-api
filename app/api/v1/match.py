"""Serviço de IA nº 3 — match (aderência) entre candidato e vaga."""

import logging
import sqlite3

from fastapi import APIRouter, Depends

from ...ai.matcher import match
from ...schemas import MatchRequest, MatchResponse
from ..deps import get_current_user, get_db, rate_limit

logger = logging.getLogger("talent.api.match")
router = APIRouter(prefix="/match", tags=["IA · Match Candidato-Vaga"])


@router.post(
    "",
    response_model=MatchResponse,
    summary="Decide a aderência de um currículo a uma vaga",
    dependencies=[Depends(rate_limit)],
)
def match_candidate(
    payload: MatchRequest,
    db: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Avalia se um candidato adere a uma vaga — distinguindo 'mesma trilha de cargo'
    de 'aderência real' (skills, senioridade e anos de experiência).
    """
    result = match(payload.resume, payload.job, db)
    logger.info("match_done user=%s decision=%s", user["username"], result["decision"])
    return MatchResponse(**result)
