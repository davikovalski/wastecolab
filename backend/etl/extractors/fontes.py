"""Download e leitura dos arquivos brutos."""

import logging
import shutil
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd

from etl.transform.ibama import COLUNAS_DESTINADOR, COLUNAS_GERADOR

log = logging.getLogger(__name__)

_USER_AGENT = "wastecolab-etl/0.1"
_TIMEOUT_S = 120


@dataclass(frozen=True)
class ArquivoBaixado:
    caminho: Path
    atualizado_na_fonte: date | None


def baixar(url: str, destino: Path, forcar: bool = False) -> ArquivoBaixado:
    """Baixa `url` para `destino` em streaming. Reaproveita o arquivo se já existir."""
    if destino.exists() and not forcar:
        modificado = datetime.fromtimestamp(destino.stat().st_mtime, tz=UTC).date()
        log.info("Usando arquivo local %s", destino)
        return ArquivoBaixado(destino, modificado)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    requisicao = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    log.info("Baixando %s", url)
    with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_S) as resposta, parcial.open("wb") as saida:
        shutil.copyfileobj(resposta, saida, length=1024 * 1024)
        cabecalho = resposta.headers.get("Last-Modified")
    parcial.replace(destino)
    atualizado = parsedate_to_datetime(cabecalho).date() if cabecalho else None
    return ArquivoBaixado(destino, atualizado)


def ler_municipios_ibge(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, usecols=["codigo_ibge", "nome", "latitude", "longitude", "codigo_uf"])


def ler_destinador(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(
        caminho, sep=";", dtype=str, encoding="utf-8", usecols=list(COLUNAS_DESTINADOR)
    )


def ler_gerador_em_lotes(caminho: Path, tamanho_lote: int) -> Iterator[pd.DataFrame]:
    """O arquivo do gerador tem ~830 MB: lê em pedaços e só as colunas usadas."""
    yield from pd.read_csv(
        caminho, sep=";", dtype=str, encoding="utf-8", usecols=list(COLUNAS_GERADOR),
        chunksize=tamanho_lote,
    )


def ler_diagnostico_municipal(caminho: Path) -> pd.DataFrame:
    # "utf-8-sig" remove o BOM que aparece em algumas edições.
    return pd.read_csv(caminho, sep=";", dtype=str, encoding="utf-8-sig")
