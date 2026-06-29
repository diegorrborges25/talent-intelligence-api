"""Tratamento de erros centralizado.

Requisito da disciplina: "Tratamento de erros". Definimos:
  - uma hierarquia de exceções de domínio (DomainError);
  - um envelope de erro padronizado (code, message, request_id, details);
  - handlers que convertem exceções em respostas HTTP consistentes e logadas.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_config import log_with_fields, request_id_ctx

logger = logging.getLogger("talent.errors")


class DomainError(Exception):
    """Erro de regra de negócio. Subclasses definem status e código."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "domain_error"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class InvalidInputError(DomainError):
    status_code = 422
    error_code = "invalid_input"


class AuthError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"


class RateLimitError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"


def _envelope(code: str, message: str, details: dict | None = None) -> dict:
    """Formato único de erro retornado pela API."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id_ctx.get(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers no app FastAPI."""

    @app.exception_handler(DomainError)
    async def _domain_handler(request: Request, exc: DomainError):
        log_with_fields(
            logger, logging.WARNING, "domain_error",
            code=exc.error_code, path=request.url.path, detail=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.error_code, exc.message, exc.details),
            headers={"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthError) else None,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        # Erros de validação do Pydantic/FastAPI -> 422 padronizado.
        log_with_fields(
            logger, logging.INFO, "validation_error",
            path=request.url.path, errors=len(exc.errors()),
        )
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "validation_error",
                "Os dados enviados são inválidos.",
                {"fields": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        # Última linha de defesa: loga o stacktrace, mas nunca vaza detalhes internos.
        logger.exception("unhandled_exception path=%s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(
                "internal_error",
                "Ocorreu um erro interno. A equipe foi notificada via logs.",
            ),
        )
