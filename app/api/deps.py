"""Dependências reutilizáveis das rotas: banco, autenticação e rate limiting."""

import logging
import time
from collections import defaultdict

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from ..config import get_settings
from ..database import connect
from ..errors import AuthError, RateLimitError
from ..security import decode_access_token

logger = logging.getLogger("talent.api.deps")

# tokenUrl aponta para o endpoint de login (aparece no botão "Authorize" do Swagger).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_db():
    """Fornece uma conexão SQLite por requisição e a fecha ao final."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Valida o Bearer Token (JWT) e retorna o payload do usuário."""
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expirado. Faça login novamente.")
    except jwt.PyJWTError:
        raise AuthError("Token inválido.")
    if "sub" not in payload:
        raise AuthError("Token sem identificação de usuário.")
    return {"username": payload["sub"], "role": payload.get("role", "recruiter")}


# --- Rate limiting em memória (janela deslizante de 60s, por usuário/IP) --- #
_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request) -> None:
    """Limita o número de requisições por minuto (proteção básica anti-abuso)."""
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    client = request.client.host if request.client else "unknown"
    auth = request.headers.get("authorization", "")
    key = f"{client}:{auth[-12:]}"  # combina IP + cauda do token

    now = time.time()
    window = _hits[key]
    # Mantém só os hits da última janela de 60s.
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= limit:
        raise RateLimitError(
            f"Limite de {limit} requisições/minuto excedido.",
            {"retry_after_seconds": 60},
        )
    window.append(now)
