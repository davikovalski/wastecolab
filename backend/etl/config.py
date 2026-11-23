"""Configuração do ETL (variáveis de ambiente ou arquivo .env)."""

from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR: Final = Path(__file__).resolve().parent.parent

URL_IBAMA_DESTINADOR: Final = (
    "https://dadosabertos.ibama.gov.br/dados/RAPP/residuoSolidosDestinador/relatorio.csv"
)
URL_IBAMA_GERADOR: Final = (
    "https://dadosabertos.ibama.gov.br/dados/RAPP/residuoSolidosGerador/relatorio.csv"
)
# Códigos IBGE e centróides dos municípios (derivado do IBGE, licença MIT).
URL_MUNICIPIOS_IBGE: Final = (
    "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
)

FONTE_IBAMA: Final = "IBAMA RAPP - Resíduos Sólidos"
FONTE_MUNICIPAL: Final = "Diagnóstico Municipal de Resíduos Sólidos"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str
    dados_dir: Path = BACKEND_DIR / "data"
    relatorios_dir: Path = BACKEND_DIR / "relatorios"
    tamanho_lote_gerador: int = 200_000
