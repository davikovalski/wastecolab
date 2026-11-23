"""Cruzamento de nomes de UF e município com a base do IBGE."""

from typing import Final

import pandas as pd

from etl.transform.texto import normalizar_nome, normalizar_serie

# (nome normalizado, UF) usado nas fontes -> nome normalizado atual no IBGE.
# Nomes antigos ou grafias diferentes encontrados no RAPP e no diagnóstico municipal.
ALIASES_MUNICIPIO: Final[dict[tuple[str, str], str]] = {
    ("moji mirim", "SP"): "mogi mirim",
    ("embu", "SP"): "embu das artes",
    ("santana do livramento", "RS"): "sant ana do livramento",
    ("assu", "RN"): "acu",
    ("santa isabel do para", "PA"): "santa izabel do para",
    ("brasopolis", "MG"): "brazopolis",
    ("sao luis do paraitinga", "SP"): "sao luiz do paraitinga",
    ("poxoreo", "MT"): "poxoreu",
    ("eldorado dos carajas", "PA"): "eldorado do carajas",
    ("lagoa do itaenga", "PE"): "lagoa de itaenga",
    ("presidente castelo branco", "SC"): "presidente castello branco",
    ("trajano de morais", "RJ"): "trajano de moraes",
    ("sao caitano", "PE"): "sao caetano",
    ("sao domingos de pombal", "PB"): "sao domingos",
    ("augusto severo", "RN"): "augusto severo campo grande",
    ("governador edson lobao", "MA"): "governador edison lobao",
    ("passos de torres", "SC"): "passo de torres",
    ("belem de sao francisco", "PE"): "belem do sao francisco",
    ("couto de magalhaes", "TO"): "couto magalhaes",
    ("presidente juscelino", "RN"): "serra caiada",
    ("sao valerio da natividade", "TO"): "sao valerio",
    ("graccho cardoso", "SE"): "gracho cardoso",
}

UF_POR_CODIGO_IBGE: Final[dict[int, str]] = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

UF_POR_NOME: Final[dict[str, str]] = {
    "rondonia": "RO", "acre": "AC", "amazonas": "AM", "roraima": "RR", "para": "PA", "amapa": "AP",
    "tocantins": "TO", "maranhao": "MA", "piaui": "PI", "ceara": "CE", "rio grande do norte": "RN",
    "paraiba": "PB", "pernambuco": "PE", "alagoas": "AL", "sergipe": "SE", "bahia": "BA",
    "minas gerais": "MG", "espirito santo": "ES", "rio de janeiro": "RJ", "sao paulo": "SP",
    "parana": "PR", "santa catarina": "SC", "rio grande do sul": "RS", "mato grosso do sul": "MS",
    "mato grosso": "MT", "goias": "GO", "distrito federal": "DF",
}


def uf_por_nome(serie: "pd.Series[str]") -> "pd.Series[str]":
    """"SAO PAULO" -> "SP". Nomes desconhecidos viram nulo."""
    return normalizar_serie(serie).map(UF_POR_NOME)


def preparar_municipios_ibge(bruto: pd.DataFrame) -> pd.DataFrame:
    """Converte o CSV de municípios (codigo_ibge, nome, latitude, longitude, codigo_uf)
    para as colunas da tabela `municipio` (sem geom; latitude/longitude são mantidas)."""
    df = pd.DataFrame(
        {
            "id_ibge": bruto["codigo_ibge"].astype("int64"),
            "nome": bruto["nome"].astype("string").str.strip(),
            "uf_sigla": bruto["codigo_uf"].astype("int64").map(UF_POR_CODIGO_IBGE),
            "latitude": bruto["latitude"].astype("float64"),
            "longitude": bruto["longitude"].astype("float64"),
        }
    )
    df["nome_normalizado"] = normalizar_serie(df["nome"])
    if df["uf_sigla"].isna().any():
        raise ValueError("Há municípios com código de UF desconhecido na base do IBGE.")
    return df


def resolver_municipio(
    nomes: "pd.Series[str]", ufs: "pd.Series[str]", municipios: pd.DataFrame
) -> "pd.Series[int]":
    """Retorna o id_ibge de cada par (nome, UF); nulo quando não encontra.

    `municipios` precisa das colunas id_ibge, nome_normalizado e uf_sigla.
    """
    normalizados = nomes.map(normalizar_nome)
    corrigidos = [
        ALIASES_MUNICIPIO.get((n, u), n) if isinstance(n, str) and isinstance(u, str) else n
        for n, u in zip(normalizados, ufs, strict=True)
    ]
    chave = pd.DataFrame({"nome_normalizado": corrigidos, "uf_sigla": list(ufs)}, index=nomes.index)
    indice = municipios.set_index(["nome_normalizado", "uf_sigla"])["id_ibge"]
    pares = pd.MultiIndex.from_frame(chave[["nome_normalizado", "uf_sigla"]])
    ids = indice.reindex(pares).to_numpy()
    return pd.Series(ids, index=nomes.index).astype("Int64")
