"""Configuração da API (variáveis de ambiente ou backend/.env)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Usuário só leitura (api_leitura). Nunca o usuário postgres.
    api_database_url: str
    # Origens liberadas no CORS, separadas por vírgula (ex.: "http://localhost:8081").
    cors_origins: Annotated[list[str], NoDecode] = []
    pool_min: int = 1
    pool_max: int = 10
    # Tempo máximo para conseguir uma conexão do pool antes de responder 503.
    pool_timeout_s: float = 5.0
    # Por quanto tempo o app pode reaproveitar uma resposta (os dados só mudam quando o ETL roda).
    cache_max_age_s: int = 300

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _separar_origens(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor


@lru_cache
def obter_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # api_database_url vem do ambiente
