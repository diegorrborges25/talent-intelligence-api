"""Configuração central da aplicação (12-factor): tudo vem de variáveis de ambiente.

Usamos `pydantic-settings`, que lê o arquivo `.env` automaticamente e valida tipos.
Qualquer valor possui default seguro, de modo que a API sobe sem nenhum `.env`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Aplicação ---
    app_name: str = "Talent Intelligence API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Logs ---
    log_level: str = "INFO"
    log_json: bool = True

    # --- Banco de dados ---
    database_path: str = "talent.db"

    # --- Segurança / JWT ---
    jwt_secret_key: str = "troque-este-segredo-em-producao-por-uma-string-aleatoria-longa-32b+"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- Usuário de demonstração (criado no seed) ---
    demo_username: str = "recruiter"
    demo_password: str = "talent123"

    # --- Rate limiting ---
    rate_limit_per_minute: int = 60

    # --- LLM opcional ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    @property
    def llm_enabled(self) -> bool:
        """LLM só é considerado ativo quando há chave configurada."""
        return bool(self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Cacheia as settings (lidas uma única vez por processo)."""
    return Settings()
