"""Conversão de números nos formatos encontrados nas fontes."""

import pandas as pd


def numero_br(serie: "pd.Series[str]") -> "pd.Series[float]":
    """Formato brasileiro do IBAMA: "30.000,00" -> 30000.0. Inválidos viram NaN."""
    texto = serie.astype("string").str.strip()
    texto = texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce")


def numero_ponto(serie: "pd.Series[str]") -> "pd.Series[float]":
    """Formato com ponto decimal (diagnóstico municipal): "226.3" -> 226.3."""
    return pd.to_numeric(serie.astype("string").str.strip(), errors="coerce")


def inteiro_ou_nulo(serie: "pd.Series[str]", minimo: int, maximo: int) -> "pd.Series[int]":
    """Converte para inteiro anulável, descartando valores fora do intervalo."""
    valores = pd.to_numeric(serie.astype("string").str.strip(), errors="coerce")
    valores = valores.where((valores >= minimo) & (valores <= maximo))
    return valores.round().astype("Int64")
