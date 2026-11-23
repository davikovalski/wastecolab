"""Relatórios de qualidade gerados pelo ETL (CSV em backend/relatorios/)."""

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def salvar_relatorio(diretorio: Path, nome: str, df: pd.DataFrame) -> Path | None:
    """Salva o DataFrame se tiver linhas e registra um aviso com a contagem."""
    if df.empty:
        return None
    diretorio.mkdir(parents=True, exist_ok=True)
    caminho = diretorio / f"{nome}.csv"
    df.to_csv(caminho, index=False)
    log.warning("%s: %d linha(s) -> %s", nome, len(df), caminho)
    return caminho
