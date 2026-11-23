"""Normalização de textos e identificadores."""

import re
import unicodedata

import pandas as pd

_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")
_NAO_DIGITO = re.compile(r"\D")


def normalizar_nome(valor: str | None) -> str | None:
    """Remove acentos, pontuação e caixa: "Sant'Ana do Livramento" -> "sant ana do livramento"."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    decomposto = unicodedata.normalize("NFKD", str(valor))
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c)).lower()
    limpo = _NAO_ALFANUMERICO.sub(" ", sem_acento).strip()
    return limpo or None


def normalizar_serie(serie: "pd.Series[str]") -> "pd.Series[str]":
    return serie.map(normalizar_nome)


def limpar_cnpj(valor: str | None) -> str | None:
    """"00.001.180/0001-26" -> "00001180000126". Retorna None se não tiver 14 dígitos."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    digitos = _NAO_DIGITO.sub("", str(valor))
    return digitos if len(digitos) == 14 else None


def limpar_texto(serie: "pd.Series[str]") -> "pd.Series[str]":
    """Remove espaços nas pontas e troca texto vazio por nulo."""
    limpa = serie.astype("string").str.strip()
    return limpa.mask(limpa == "")
