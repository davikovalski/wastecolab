"""Transformações dos arquivos de Resíduos Sólidos do RAPP/IBAMA."""

from dataclasses import dataclass
from typing import Final, Literal

import pandas as pd

from etl.transform.localidades import uf_por_nome
from etl.transform.numeros import numero_br
from etl.transform.texto import limpar_cnpj, limpar_texto, normalizar_nome

CategoriaOperacao = Literal["valorizacao", "aterro", "eliminacao"]

OPERACOES_ATERRO: Final = frozenset({"D1", "D4", "D5"})

UNIDADES: Final[dict[str, str]] = {
    "kilogramas (kg)": "kg",
    "kilogramas": "kg",
    "quilogramas": "kg",
    "kg": "kg",
    "litro (l)": "l",
    "litro": "l",
    "litros": "l",
    "unidade (un)": "un",
    "unidade": "un",
}

COLUNAS_DESTINADOR: Final[dict[str, str]] = {
    "CNPJ do destinador": "destinador_cnpj",
    "Razão Social do destinador": "destinador_razao_social",
    "Estado": "estado",
    "Município": "municipio",
    "Categoria de Atividade": "categoria_atividade",
    "Detalhe": "detalhe_atividade",
    "CNPJ do gerador do resíduo": "gerador_cnpj",
    "Raz soc do gerador do resíduo": "gerador_razao_social",
    "Cód. Resíduo": "codigo_residuo",
    "Desc. Resíduo": "residuo_descricao",
    "Ano - destinação": "ano",
    "Quant. destinada": "quantidade",
    "Unidade": "unidade",
    "Tipo de destinação": "tipo_destinacao",
    "Situação Cadastral": "situacao_cadastral",
}

COLUNAS_GERADOR: Final[dict[str, str]] = {
    "CNPJ do gerador": "cnpj",
    "Razão Social do gerador": "razao_social",
    "Estado": "estado",
    "Município": "municipio",
    "Categoria de Atividade": "categoria_atividade",
    "Detalhe": "detalhe_atividade",
    "Ano da geração": "ano",
    "Cód. Resíduo": "codigo_residuo",
    "Tipo de Resíduo": "residuo_descricao",
    "Classificação Resíduo": "classificacao",
    "Situação Cadastral": "situacao_cadastral",
}

_PADRAO_OPERACAO: Final = r"^\s*([RD]\d{1,2})\b"


def classificar_operacao(codigo: str) -> CategoriaOperacao:
    """R* = valorização; D1, D4, D5 = aterro; demais D = eliminação."""
    if codigo.startswith("R"):
        return "valorizacao"
    if codigo in OPERACOES_ATERRO:
        return "aterro"
    if codigo.startswith("D"):
        return "eliminacao"
    raise ValueError(f"Código de operação desconhecido: {codigo!r}")


def normalizar_unidade(serie: "pd.Series[str]") -> "pd.Series[str]":
    return serie.astype("string").str.strip().str.lower().map(UNIDADES)


def normalizar_codigo_residuo(serie: "pd.Series[str]") -> "pd.Series[str]":
    """Mantém só dígitos e completa com zeros à esquerda (ex.: "70213" -> "070213")."""
    digitos = serie.astype("string").str.replace(r"\D", "", regex=True)
    digitos = digitos.mask(digitos == "")
    return digitos.str.zfill(6).where(digitos.str.len() <= 6)


@dataclass(frozen=True)
class ResultadoDestinador:
    movimentacoes: pd.DataFrame
    destinadores: pd.DataFrame
    geradores: pd.DataFrame
    codigos: pd.DataFrame
    operacoes: pd.DataFrame
    rejeitadas: pd.DataFrame


def transformar_destinador(bruto: pd.DataFrame) -> ResultadoDestinador:
    """Transforma o CSV "Resíduos Sólidos – Destinador" (todas as colunas como texto)."""
    df = bruto.rename(columns=COLUNAS_DESTINADOR)[list(COLUNAS_DESTINADOR.values())].copy()
    df["gerador_cnpj"] = df["gerador_cnpj"].map(limpar_cnpj)
    df["destinador_cnpj"] = df["destinador_cnpj"].map(limpar_cnpj)
    df["codigo_residuo"] = normalizar_codigo_residuo(df["codigo_residuo"])
    df["operacao"] = df["tipo_destinacao"].astype("string").str.extract(_PADRAO_OPERACAO, expand=False)
    df["operacao_descricao"] = (
        df["tipo_destinacao"].astype("string").str.replace(r"^\s*[RD]\d{1,2}\s*-\s*", "", regex=True)
    )
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["quantidade"] = numero_br(df["quantidade"])
    df["unidade"] = normalizar_unidade(df["unidade"])
    df["uf_sigla"] = uf_por_nome(df["estado"])
    for coluna in ("destinador_razao_social", "gerador_razao_social", "residuo_descricao",
                   "categoria_atividade", "detalhe_atividade", "situacao_cadastral", "municipio"):
        df[coluna] = limpar_texto(df[coluna])

    obrigatorias = ["gerador_cnpj", "destinador_cnpj", "codigo_residuo", "operacao", "ano", "unidade"]
    invalida = df[obrigatorias].isna().any(axis=1)
    rejeitadas = df[invalida].assign(motivo="campo obrigatório ausente ou inválido")
    validas = df[~invalida]

    chave = ["gerador_cnpj", "destinador_cnpj", "codigo_residuo", "operacao", "ano", "unidade"]
    movimentacoes = validas.groupby(chave, as_index=False, sort=False).agg(
        quantidade=("quantidade", "sum"), _informadas=("quantidade", "count")
    )
    # Soma de quantidades todas vazias continua "não informada" (e não zero).
    movimentacoes["quantidade"] = movimentacoes["quantidade"].where(movimentacoes["_informadas"] > 0)
    movimentacoes = movimentacoes.drop(columns=["_informadas"])

    destinadores = (
        validas.sort_values("ano")
        .drop_duplicates("destinador_cnpj", keep="last")
        .rename(columns={"destinador_cnpj": "cnpj", "destinador_razao_social": "razao_social"})
        [["cnpj", "razao_social", "uf_sigla", "municipio", "categoria_atividade",
          "detalhe_atividade", "situacao_cadastral"]]
        .reset_index(drop=True)
    )

    geradores = (
        validas.sort_values("ano")
        .drop_duplicates("gerador_cnpj", keep="last")
        .rename(columns={"gerador_cnpj": "cnpj", "gerador_razao_social": "razao_social"})
        [["cnpj", "razao_social"]]
        .reset_index(drop=True)
    )

    codigos = (
        validas.dropna(subset=["residuo_descricao"])
        .drop_duplicates("codigo_residuo", keep="last")
        .rename(columns={"codigo_residuo": "codigo", "residuo_descricao": "descricao"})
        [["codigo", "descricao"]]
        .reset_index(drop=True)
    )

    operacoes = (
        validas.drop_duplicates("operacao")
        .rename(columns={"operacao": "codigo", "operacao_descricao": "descricao"})[["codigo", "descricao"]]
        .reset_index(drop=True)
    )
    operacoes["categoria"] = operacoes["codigo"].map(classificar_operacao)

    return ResultadoDestinador(
        movimentacoes=movimentacoes.reset_index(drop=True),
        destinadores=destinadores,
        geradores=geradores,
        codigos=codigos,
        operacoes=operacoes,
        rejeitadas=rejeitadas.reset_index(drop=True),
    )


@dataclass(frozen=True)
class LoteGerador:
    estabelecimentos: pd.DataFrame
    codigos: pd.DataFrame


def transformar_lote_gerador(bruto: pd.DataFrame) -> LoteGerador:
    """Transforma um pedaço do CSV "Resíduos Sólidos – Gerador".

    Para cada CNPJ guarda os dados cadastrais da linha mais recente; para cada código,
    a descrição completa e se é perigoso.
    """
    df = bruto.rename(columns=COLUNAS_GERADOR)[list(COLUNAS_GERADOR.values())].copy()
    df["cnpj"] = df["cnpj"].map(limpar_cnpj)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["uf_sigla"] = uf_por_nome(df["estado"])
    df["codigo_residuo"] = normalizar_codigo_residuo(df["codigo_residuo"])
    for coluna in ("razao_social", "municipio", "categoria_atividade", "detalhe_atividade",
                   "situacao_cadastral", "residuo_descricao"):
        df[coluna] = limpar_texto(df[coluna])

    estabelecimentos = (
        df.dropna(subset=["cnpj", "razao_social"])
        .sort_values("ano", na_position="first")
        .drop_duplicates("cnpj", keep="last")
        [["cnpj", "razao_social", "uf_sigla", "municipio", "categoria_atividade",
          "detalhe_atividade", "situacao_cadastral", "ano"]]
    )

    classificacao = df["classificacao"].map(normalizar_nome)
    df["perigoso"] = classificacao.map({"perigoso": True, "nao perigoso": False}).astype("boolean")
    codigos = (
        df.dropna(subset=["codigo_residuo", "residuo_descricao"])
        .drop_duplicates("codigo_residuo", keep="last")
        .rename(columns={"codigo_residuo": "codigo", "residuo_descricao": "descricao"})
        [["codigo", "descricao", "perigoso"]]
    )
    return LoteGerador(
        estabelecimentos=estabelecimentos.reset_index(drop=True),
        codigos=codigos.reset_index(drop=True),
    )


def consolidar_lotes_gerador(lotes: list[LoteGerador]) -> LoteGerador:
    """Junta os lotes mantendo o cadastro mais recente de cada CNPJ."""
    if not lotes:
        vazio = pd.DataFrame()
        return LoteGerador(estabelecimentos=vazio, codigos=vazio)
    estabelecimentos = (
        pd.concat([lote.estabelecimentos for lote in lotes], ignore_index=True)
        .sort_values("ano", na_position="first")
        .drop_duplicates("cnpj", keep="last")
        .drop(columns=["ano"])
        .reset_index(drop=True)
    )
    codigos_todos = pd.concat([lote.codigos for lote in lotes], ignore_index=True)
    # Prefere a linha que informa se o resíduo é perigoso.
    codigos = (
        codigos_todos.assign(_tem_classe=codigos_todos["perigoso"].notna())
        .sort_values("_tem_classe")
        .drop_duplicates("codigo", keep="last")
        .drop(columns=["_tem_classe"])
        .reset_index(drop=True)
    )
    return LoteGerador(estabelecimentos=estabelecimentos, codigos=codigos)
