"""Transformação do Diagnóstico Municipal (CSV "explodido": uma linha por
tipo de resíduo x material x destinação x meta)."""

import math
import re
from dataclasses import dataclass
from typing import Final

import pandas as pd

from etl.transform.numeros import inteiro_ou_nulo, numero_ponto
from etl.transform.texto import limpar_texto, normalizar_nome

COLUNAS: Final[dict[str, str]] = {
    "Declaração": "declaracao_id",
    "Ano": "ano",
    "Ano Referencia": "ano_referencia",
    "Data Criação": "data_criacao",
    "Data Entrega": "data_entrega",
    "Declarante": "declarante",
    "Município Declarante": "municipio",
    "UF Declarante": "uf_sigla",
    "orr_descricao": "tipo_residuo",
    "Possui Coleta Seletiva Implantada": "possui_coleta_seletiva",
    "Possui Plano de Gestão": "possui_plano_gestao",
    "Link do Plano": "link_plano",
    "Periocidade da Revisão": "periodicidade_revisao_texto",
    "Ano Última Versão Plano": "ano_ultima_versao_plano",
    "Massa (TON)": "massa_ton",
    "Caracterização - Descrição": "material",
    "Caracterização - Percentual": "material_percentual",
    "Caracterização - Destinação": "destinacao",
    "Caracterização - Destinação percentual": "destinacao_percentual",
    "Meta Informada": "meta_tipo",
    "Meta - Valor Atual": "meta_valor_atual",
    "Meta - Valor": "meta_valor",
    "Meta - Prazo": "meta_prazo",
    "Meta - Programa": "meta_programa",
    "Meta - Programa - Descritivo": "meta_programa_descritivo",
}

# Destinação do diagnóstico municipal -> categoria (mesma classificação confirmada para o MVP).
CATEGORIA_DESTINACAO: Final[dict[str, str]] = {
    "reciclagem": "valorizacao",
    "tratamento": "valorizacao",
    "tratamento com aproveitamento energetico": "valorizacao",
    "aproveitamento na agricultura": "valorizacao",
    "disposicao ordenada em solo para recuperacao de areas degradadas": "valorizacao",
    "disposicao final em aterro sanitario": "aterro",
    "disposicao final em lixao": "eliminacao",
    "vala especifica de rss": "eliminacao",
}

TIPO_META: Final[dict[str, str]] = {
    "coleta seletiva": "coleta_seletiva",
    "reciclagem": "reciclagem",
    "reducao": "reducao",
    "reutilizacao": "reutilizacao",
    "eliminacao e recuperacao de lixoes": "eliminacao_lixoes",
}

_ANO: Final = re.compile(r"^(20\d{2})$")
_QUANTIDADE: Final = re.compile(r"^(\d{1,3})\s*(anos?|mes(?:es)?)?$")


def categoria_destinacao(descricao: str) -> str:
    chave = normalizar_nome(descricao)
    if chave is None or chave not in CATEGORIA_DESTINACAO:
        raise ValueError(f"Destinação municipal sem categoria: {descricao!r}")
    return CATEGORIA_DESTINACAO[chave]


def normalizar_prazo(texto: str | None, ano_referencia: int) -> int | None:
    """"2026" -> 2026; "2 anos" -> ref+2; "12 MESES" -> ref+1; "anual" -> ref+1."""
    chave = normalizar_nome(texto)
    if chave is None:
        return None
    if chave == "anual":
        return ano_referencia + 1
    if (ano := _ANO.match(chave)) is not None:
        return int(ano.group(1))
    if (qtd := _QUANTIDADE.match(chave)) is not None:
        numero = int(qtd.group(1))
        unidade = qtd.group(2) or "anos"
        if unidade.startswith("mes"):
            return ano_referencia + max(1, math.ceil(numero / 12))
        return ano_referencia + numero if numero <= 50 else None
    return None


def _sim_nao(serie: "pd.Series[str]") -> "pd.Series[bool]":
    return serie.map(normalizar_nome).map({"sim": True, "nao": False}).astype("boolean")


@dataclass(frozen=True)
class ResultadoMunicipal:
    declaracoes: pd.DataFrame
    tipos_residuo: pd.DataFrame
    materiais: pd.DataFrame
    destinacoes: pd.DataFrame
    geracoes: pd.DataFrame
    composicoes: pd.DataFrame
    destinacoes_material: pd.DataFrame
    metas: pd.DataFrame


def transformar_diagnostico(bruto: pd.DataFrame) -> ResultadoMunicipal:
    df = bruto.rename(columns=COLUNAS)[list(COLUNAS.values())].drop_duplicates().copy()
    for coluna in ("declarante", "municipio", "uf_sigla", "tipo_residuo", "link_plano", "material",
                   "destinacao", "meta_tipo", "meta_prazo", "meta_programa",
                   "meta_programa_descritivo", "periodicidade_revisao_texto"):
        df[coluna] = limpar_texto(df[coluna])
    df["declaracao_id"] = pd.to_numeric(df["declaracao_id"], errors="raise").astype("int64")
    df["ano"] = pd.to_numeric(df["ano"]).astype("int64")
    df["ano_referencia"] = pd.to_numeric(df["ano_referencia"]).astype("int64")
    for coluna in ("massa_ton", "material_percentual", "destinacao_percentual",
                   "meta_valor_atual", "meta_valor"):
        df[coluna] = numero_ponto(df[coluna])
    # Há percentuais impossíveis na fonte (ex.: 2000): viram "não informado".
    for coluna in ("material_percentual", "destinacao_percentual"):
        df[coluna] = df[coluna].where(df[coluna].between(0, 100))
    df["massa_ton"] = df["massa_ton"].where(df["massa_ton"] >= 0)

    declaracoes = df.drop_duplicates("declaracao_id")[[
        "declaracao_id", "municipio", "uf_sigla", "declarante", "ano", "ano_referencia",
        "data_criacao", "data_entrega", "possui_coleta_seletiva", "possui_plano_gestao",
        "link_plano", "periodicidade_revisao_texto", "ano_ultima_versao_plano",
    ]].rename(columns={"declaracao_id": "id"}).copy()
    declaracoes["data_criacao"] = pd.to_datetime(declaracoes["data_criacao"], format="%d/%m/%Y").dt.date
    declaracoes["data_entrega"] = pd.to_datetime(declaracoes["data_entrega"], format="%d/%m/%Y").dt.date
    declaracoes["possui_coleta_seletiva"] = _sim_nao(declaracoes["possui_coleta_seletiva"])
    declaracoes["possui_plano_gestao"] = _sim_nao(declaracoes["possui_plano_gestao"])
    declaracoes["periodicidade_revisao_anos"] = inteiro_ou_nulo(
        declaracoes["periodicidade_revisao_texto"], 0, 30
    )
    declaracoes["ano_ultima_versao_plano"] = inteiro_ou_nulo(
        declaracoes["ano_ultima_versao_plano"], 1950, 2100
    )

    tipos_residuo = pd.DataFrame(
        {"descricao": sorted(df["tipo_residuo"].dropna().unique())}
    )
    materiais = (
        df.dropna(subset=["material"]).drop_duplicates("material")
        [["material", "tipo_residuo"]]
        .rename(columns={"material": "descricao", "tipo_residuo": "tipo_residuo_descricao"})
        .sort_values("descricao").reset_index(drop=True)
    )
    destinacoes = pd.DataFrame({"descricao": sorted(df["destinacao"].dropna().unique())})
    destinacoes["categoria"] = destinacoes["descricao"].map(categoria_destinacao)

    com_tipo = df.dropna(subset=["tipo_residuo"])
    geracoes = com_tipo.groupby(["declaracao_id", "tipo_residuo"], as_index=False).agg(
        massa_ton=("massa_ton", "first")
    )
    com_material = com_tipo.dropna(subset=["material"])
    composicoes = com_material.groupby(
        ["declaracao_id", "tipo_residuo", "material"], as_index=False
    ).agg(percentual=("material_percentual", "first"))
    destinacoes_material = com_material.dropna(subset=["destinacao"]).groupby(
        ["declaracao_id", "tipo_residuo", "material", "destinacao"], as_index=False
    ).agg(percentual=("destinacao_percentual", "first"))

    metas = df.dropna(subset=["meta_tipo"]).drop_duplicates(
        ["declaracao_id", "meta_tipo", "meta_valor_atual", "meta_valor", "meta_prazo", "meta_programa",
         "meta_programa_descritivo"]
    )[["declaracao_id", "ano_referencia", "meta_tipo", "meta_valor_atual", "meta_valor", "meta_prazo",
       "meta_programa", "meta_programa_descritivo"]].copy()
    metas["tipo"] = metas["meta_tipo"].map(normalizar_nome).map(TIPO_META)
    if metas["tipo"].isna().any():
        desconhecidos = sorted(metas.loc[metas["tipo"].isna(), "meta_tipo"].unique())
        raise ValueError(f"Tipos de meta desconhecidos: {desconhecidos}")
    metas["prazo_ano"] = [
        normalizar_prazo(texto if isinstance(texto, str) else None, int(ref))
        for texto, ref in zip(metas["meta_prazo"], metas["ano_referencia"], strict=True)
    ]
    metas["prazo_ano"] = metas["prazo_ano"].astype("Int64")
    metas = metas.rename(columns={
        "meta_valor_atual": "valor_atual", "meta_valor": "valor_meta", "meta_prazo": "prazo_texto",
        "meta_programa": "programa", "meta_programa_descritivo": "programa_descritivo",
    })[["declaracao_id", "tipo", "valor_atual", "valor_meta", "prazo_texto", "prazo_ano", "programa",
        "programa_descritivo"]]

    return ResultadoMunicipal(
        declaracoes=declaracoes.reset_index(drop=True),
        tipos_residuo=tipos_residuo,
        materiais=materiais,
        destinacoes=destinacoes,
        geracoes=geracoes,
        composicoes=composicoes,
        destinacoes_material=destinacoes_material,
        metas=metas.reset_index(drop=True),
    )


def marcar_vigentes(declaracoes: pd.DataFrame) -> "pd.Series[bool]":
    """Por município (municipio_id), vale a declaração com a data de entrega mais recente
    (desempate pelo maior id)."""
    ordenadas = declaracoes.sort_values(["municipio_id", "data_entrega", "id"])
    ultimas = ordenadas.drop_duplicates("municipio_id", keep="last")["id"]
    return declaracoes["id"].isin(ultimas) & declaracoes["municipio_id"].notna()
