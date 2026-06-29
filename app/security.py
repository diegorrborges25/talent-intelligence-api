"""Segurança: hashing de senha (PBKDF2/stdlib) e tokens JWT (PyJWT).

Requisitos da disciplina: "Segurança" e "Autenticação".
  - Senhas nunca são armazenadas em texto puro: usamos PBKDF2-HMAC-SHA256 com salt
    (tudo via `hashlib` da stdlib — sem dependências compiladas, roda em qualquer SO).
  - Acesso aos endpoints de IA exige Bearer Token (JWT) emitido em /api/v1/auth/token.
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import get_settings

_PBKDF2_ROUNDS = 200_000


def hash_password(password: str) -> str:
    """Gera hash PBKDF2 no formato `pbkdf2_sha256$rounds$salt_hex$hash_hex`."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verifica a senha contra o hash armazenado (comparação em tempo constante)."""
    try:
        algo, rounds_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds_s)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_access_token(subject: str, role: str = "recruiter") -> str:
    """Emite um JWT assinado com expiração configurável."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decodifica e valida o JWT. Lança jwt.PyJWTError em caso de falha."""
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
