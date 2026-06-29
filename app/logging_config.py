"""Logging estruturado (JSON) com rotação em arquivo.

Requisito da disciplina: "Logs". Aqui entregamos:
  - logs estruturados em JSON (fáceis de ingerir em ELK/Datadog/Loki);
  - um `request_id` correlacionando todas as linhas de uma mesma requisição;
  - saída simultânea em stdout e em arquivo rotativo (logs/app.log).
"""

import json
import logging
import sys
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Variável de contexto: cada requisição injeta seu id e ele aparece em todo log.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """Formata cada registro de log como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        # Campos extras explicitamente anexados (ex.: latency_ms, path, status).
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """Formato legível para humanos (usado quando LOG_JSON=false)."""

    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, '%H:%M:%S')} "
            f"[{record.levelname}] [{request_id_ctx.get()}] "
            f"{record.name}: {record.getMessage()}"
        )
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging(level: str = "INFO", as_json: bool = True) -> None:
    """Configura o logger raiz com handlers de console e arquivo."""
    formatter: logging.Formatter = JsonFormatter() if as_json else PlainFormatter()

    root = logging.getLogger()
    root.setLevel(level.upper())
    # Evita handlers duplicados em reloads/testes.
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Reduz ruído do uvicorn de acesso (usamos nosso próprio middleware de acesso).
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


def log_with_fields(logger: logging.Logger, level: int, message: str, **fields) -> None:
    """Helper para logar uma mensagem anexando campos estruturados extras."""
    record_extra = {"extra_fields": fields}
    logger.log(level, message, extra=record_extra)
