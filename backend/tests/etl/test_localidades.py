from pathlib import Path

import pandas as pd
import pytest

from etl.transform.localidades import (
    ALIASES_MUNICIPIO,
    preparar_municipios_ibge,
    resolver_municipio,
    uf_por_nome,
)

IBGE_BRUTO = pd.DataFrame(
    {
        "codigo_ibge": [3530805, 3515004, 4317103, 3550308],
        "nome": ["Mogi Mirim", "Embu das Artes", "Sant'Ana do Livramento", "São Paulo"],
        "latitude": [-22.43, -23.65, -30.89, -23.53],
        "longitude": [-46.95, -46.85, -55.53, -46.63],
        "codigo_uf": [35, 35, 43, 35],
    }
)


def test_uf_por_nome():
    resultado = uf_por_nome(pd.Series(["SAO PAULO", "Rio Grande do Sul", "ESPIRITO SANTO", "Atlântida"]))
    assert resultado.tolist()[:3] == ["SP", "RS", "ES"]
    assert pd.isna(resultado.iloc[3])


def test_preparar_municipios_ibge():
    municipios = preparar_municipios_ibge(IBGE_BRUTO)
    assert municipios.loc[2, "nome_normalizado"] == "sant ana do livramento"
    assert municipios["uf_sigla"].tolist() == ["SP", "SP", "RS", "SP"]


def test_preparar_municipios_ibge_rejeita_uf_desconhecida():
    with pytest.raises(ValueError):
        preparar_municipios_ibge(IBGE_BRUTO.assign(codigo_uf=99))


def test_resolver_municipio_usa_aliases_e_marca_nao_encontrados():
    municipios = preparar_municipios_ibge(IBGE_BRUTO)
    nomes = pd.Series(["MOJI MIRIM", "EMBU", "SANTANA DO LIVRAMENTO", "São Paulo", "Inexistente", None])
    ufs = pd.Series(["SP", "SP", "RS", "SP", "SP", "SP"])
    ids = resolver_municipio(nomes, ufs, municipios)
    assert ids.tolist()[:4] == [3530805, 3515004, 4317103, 3550308]
    assert ids.iloc[4:].isna().all()


def test_mesmo_nome_em_ufs_diferentes_nao_se_confunde():
    municipios = preparar_municipios_ibge(IBGE_BRUTO)
    ids = resolver_municipio(pd.Series(["Sao Paulo"]), pd.Series(["RJ"]), municipios)
    assert ids.isna().all()


ARQUIVO_IBGE = Path(__file__).resolve().parents[2] / "data" / "municipios_ibge.csv"


@pytest.mark.skipif(not ARQUIVO_IBGE.exists(), reason="base do IBGE não baixada")
def test_todos_os_aliases_existem_no_ibge():
    municipios = preparar_municipios_ibge(pd.read_csv(ARQUIVO_IBGE))
    chaves = set(zip(municipios["nome_normalizado"], municipios["uf_sigla"], strict=True))
    faltando = [(destino, uf) for (_, uf), destino in ALIASES_MUNICIPIO.items() if (destino, uf) not in chaves]
    assert faltando == []
