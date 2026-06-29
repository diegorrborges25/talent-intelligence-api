"""Endpoint de autenticação — OAuth2 Password Flow emitindo JWT."""

import logging
import sqlite3

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ...config import get_settings
from ...errors import AuthError
from ...schemas import Token
from ...security import create_access_token, verify_password
from ..deps import get_db

logger = logging.getLogger("talent.api.auth")
router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/token", response_model=Token, summary="Login e emissão de token JWT")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    """Recebe usuário/senha (form-urlencoded) e retorna um access token Bearer.

    Credenciais de demonstração (definidas no `.env`): **recruiter / talent123**.
    """
    row = db.execute(
        "SELECT username, password_hash, role FROM users WHERE username = ?",
        (form.username,),
    ).fetchone()

    if not row or not verify_password(form.password, row["password_hash"]):
        logger.warning("login_failed user=%s", form.username)
        raise AuthError("Usuário ou senha inválidos.")

    token = create_access_token(subject=row["username"], role=row["role"])
    logger.info("login_ok user=%s", form.username)
    return Token(
        access_token=token,
        expires_in_minutes=get_settings().access_token_expire_minutes,
    )
