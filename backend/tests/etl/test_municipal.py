from datetime import date

import pandas as pd
import pytest

from etl.transform.municipal import (
    COLUNAS,
    categoria_destinacao,
    marcar_vigentes,
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


def test_marcar_vigentes_usa_entrega_mais_recente():
    declaracoes = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "municipio_id": pd.array([10, 10, 20, None], dtype="Int64"),
        "data_entrega": [date(2025, 4, 1), date(2025, 5, 1), date(2025, 4, 1), date(2025, 4, 1)],
    })
    assert marcar_vigentes(declaracoes).tolist() == [False, True, True, False]
