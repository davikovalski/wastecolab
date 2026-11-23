from datetime import date

import pandas as pd
import pytest

from etl.transform.municipal import (
    COLUNAS,
    categoria_destinacao,
    normalizar_prazo,
    transformar_diagnostico,
)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("2026", 2026), ("2 anos", 2026), ("02 anos", 2026), ("1 ANO ", 2025), ("12 MESES", 2025),
     ("8 meses", 2025), ("24 meses", 2026), ("anual", 2025), ("5", 2029), ("sem prazo", None), (None, None)],
)
def test_normalizar_prazo(texto, esperado):
    assert normalizar_prazo(texto, 2024) == esperado


def test_categoria_destinacao():
    assert categoria_destinacao("Reciclagem") == "valorizacao"
    assert categoria_destinacao("Disposição ordenada em solo para recuperação de áreas degradadas ") == "valorizacao"
    assert categoria_destinacao("Disposição Final em Aterro Sanitário") == "aterro"
    assert categoria_destinacao("Disposição Final em Lixão") == "eliminacao"
    with pytest.raises(ValueError):
        categoria_destinacao("Outra coisa")


def _linha(**valores: str) -> dict[str, str]:
    base = {coluna: "" for coluna in COLUNAS}
    base.update({
        "Declaração": "14255", "Ano": "2025", "Ano Referencia": "2024", "Data Criação": "07/05/2025",
        "Data Entrega": "21/05/2025", "Declarante": "Cruzeiro do Sul", "Município Declarante": "Cruzeiro do Sul",
        "UF Declarante": "AC", "orr_descricao": "Resíduos domiciliares",
        "Possui Coleta Seletiva Implantada": "Não", "Possui Plano de Gestão": "Sim",
        "Periocidade da Revisão": "04", "Ano Última Versão Plano": "2018", "Massa (TON)": "226.3",
        "Caracterização - Descrição": "Plástico", "Caracterização - Percentual": "15",
        "Caracterização - Destinação": "Reciclagem", "Caracterização - Destinação percentual": "40",
        "Meta Informada": "Reciclagem", "Meta - Valor Atual": "795", "Meta - Valor": "1590",
        "Meta - Prazo": "2026",
    })
    base.update(valores)
    return base


def test_transformar_diagnostico_normaliza_linhas_explodidas():
    bruto = pd.DataFrame([
        _linha(),
        _linha(**{"Caracterização - Destinação": "Disposição Final em Aterro Sanitário",
                  "Caracterização - Destinação percentual": "60"}),
        _linha(**{"Meta Informada": "Coleta Seletiva", "Meta - Prazo": "2 anos"}),
        _linha(**{"Caracterização - Percentual": "2000"}),  # percentual impossível
        _linha(),  # duplicada exata
    ], dtype="string").replace({"": pd.NA})
    r = transformar_diagnostico(bruto)

    assert len(r.declaracoes) == 1
    decl = r.declaracoes.iloc[0]
    assert decl["data_entrega"] == date(2025, 5, 21)
    assert bool(decl["possui_plano_gestao"]) and not bool(decl["possui_coleta_seletiva"])
    assert decl["periodicidade_revisao_anos"] == 4

    assert len(r.geracoes) == 1 and r.geracoes["massa_ton"].iloc[0] == pytest.approx(226.3)
    assert r.composicoes["percentual"].iloc[0] == 15
    assert sorted(r.destinacoes_material["destinacao"]) == ["Disposição Final em Aterro Sanitário", "Reciclagem"]
    assert set(r.destinacoes.set_index("descricao")["categoria"]) == {"valorizacao", "aterro"}

    metas = r.metas.set_index("tipo")
    assert metas.loc["reciclagem", "prazo_ano"] == 2026
    assert metas.loc["coleta_seletiva", "prazo_ano"] == 2026


def test_transformar_diagnostico_rejeita_meta_desconhecida():
    bruto = pd.DataFrame([_linha(**{"Meta Informada": "Algo novo"})], dtype="string")
    with pytest.raises(ValueError, match="Tipos de meta"):
        transformar_diagnostico(bruto)


def test_edicao_2022_com_bom_espacos_ni_e_numeros_brasileiros():
    linha = _linha(**{
        "Massa (TON)": "1.681,20", "Caracterização - Percentual": "N/I",
        "Caracterização - Destinação percentual": "57,89", "Meta - Valor": "1.320.000",
        "Meta - Valor Atual": "N/I", "Link do Plano": "N/I", "Declaração": "8.602",
    })
    # Nomes de coluna com BOM e espaços, valores com espaços à direita (como no arquivo de 2022).
    bruto = pd.DataFrame([{f"\ufeff{k}" if k == "Declaração" else f"{k}   ": f"{v}    " for k, v in linha.items()}])
    r = transformar_diagnostico(bruto)

    assert r.geracoes["massa_ton"].iloc[0] == pytest.approx(1681.2)
    assert pd.isna(r.composicoes["percentual"].iloc[0])
    assert r.destinacoes_material["percentual"].iloc[0] == pytest.approx(57.89)
    assert r.metas["valor_meta"].iloc[0] == pytest.approx(1_320_000)
    assert pd.isna(r.metas["valor_atual"].iloc[0])
    assert pd.isna(r.declaracoes["link_plano"].iloc[0])
    assert r.declaracoes["declarante"].iloc[0] == "Cruzeiro do Sul"
    assert r.declaracoes["id"].iloc[0] == 8602  # "8.602" é separador de milhar, não decimal


def test_material_ni_e_ignorado():
    bruto = pd.DataFrame([_linha(), _linha(**{"Caracterização - Descrição": "N/I",
                                              "Caracterização - Destinação": "N/I"})])
    r = transformar_diagnostico(bruto)
    assert r.materiais["descricao"].tolist() == ["Plástico"]
    assert len(r.composicoes) == 1


def test_coluna_ausente_gera_erro_claro():
    bruto = pd.DataFrame([_linha()]).drop(columns=["Massa (TON)"])
    with pytest.raises(ValueError, match="Massa"):
        transformar_diagnostico(bruto)
