import pandas as pd
import pytest

from etl.pipelines import montar_estabelecimentos
from etl.transform.ibama import (
    classificar_operacao,
    consolidar_lotes_gerador,
    normalizar_codigo_residuo,
    normalizar_unidade,
    transformar_destinador,
    transformar_lote_gerador,
)


@pytest.mark.parametrize(
    ("codigo", "categoria"),
    [("R1", "valorizacao"), ("R13", "valorizacao"), ("D1", "aterro"), ("D4", "aterro"),
     ("D5", "aterro"), ("D10", "eliminacao"), ("D13", "eliminacao")],
)
def test_classificar_operacao(codigo, categoria):
    assert classificar_operacao(codigo) == categoria


def test_classificar_operacao_desconhecida():
    with pytest.raises(ValueError):
        classificar_operacao("X1")


def test_normalizar_unidade():
    resultado = normalizar_unidade(pd.Series(["kilogramas (kg)", "Litro (L)", "Unidade (UN)", "kilogramas", "?"]))
    assert resultado.tolist()[:4] == ["kg", "l", "un", "kg"]
    assert pd.isna(resultado.iloc[4])


def test_normalizar_codigo_residuo():
    resultado = normalizar_codigo_residuo(pd.Series(["070213", "70213", "07 02 13", "1234567", ""]))
    assert resultado.tolist()[:3] == ["070213", "070213", "070213"]
    assert resultado.iloc[3:].isna().all()


def test_transformar_destinador_agrega_e_rejeita(destinador_bruto):
    r = transformar_destinador(destinador_bruto)

    assert len(r.rejeitadas) == 1
    aterro = r.movimentacoes[(r.movimentacoes["operacao"] == "D5")]
    assert len(aterro) == 1  # as duas linhas de 2024 foram somadas
    assert aterro["quantidade"].iloc[0] == pytest.approx(15000.5)
    assert aterro["gerador_cnpj"].iloc[0] == "11111111000111"
    assert set(r.movimentacoes["unidade"]) == {"kg", "l"}

    assert set(r.destinadores["cnpj"]) == {"22222222000122", "33333333000133", "44444444000144"}
    longe = r.destinadores.set_index("cnpj").loc["44444444000144"]
    assert longe["uf_sigla"] == "RS"

    assert r.operacoes.set_index("codigo")["categoria"].to_dict() == {"D5": "aterro", "R3": "valorizacao"}
    assert r.operacoes.set_index("codigo").loc["D5", "descricao"] == "Aterramentos especialmente projetados"


def test_lote_gerador_guarda_cadastro_mais_recente(gerador_bruto):
    lote = transformar_lote_gerador(gerador_bruto)
    cadastro = lote.estabelecimentos.set_index("cnpj").loc["11111111000111"]
    assert cadastro["razao_social"] == "GERADORA EXEMPLO LTDA"
    assert lote.codigos.set_index("codigo").loc["070213", "perigoso"] == False  # noqa: E712


def test_consolidar_lotes_prefere_ano_recente_e_classe_informada(gerador_bruto):
    lote_antigo = transformar_lote_gerador(gerador_bruto.iloc[[0]])
    lote_novo = transformar_lote_gerador(gerador_bruto.iloc[[1, 2]])
    final = consolidar_lotes_gerador([lote_novo, lote_antigo])
    cadastro = final.estabelecimentos.set_index("cnpj")
    assert cadastro.loc["11111111000111", "razao_social"] == "GERADORA EXEMPLO LTDA"
    assert "ano" not in final.estabelecimentos.columns
    assert final.codigos.set_index("codigo").loc["070213", "perigoso"] == False  # noqa: E712


def test_consolidar_lotes_vazio():
    final = consolidar_lotes_gerador([])
    assert final.estabelecimentos.empty


def test_montar_estabelecimentos_prioriza_arquivo_do_gerador(destinador_bruto, gerador_bruto):
    r = transformar_destinador(destinador_bruto)
    cadastros = consolidar_lotes_gerador([transformar_lote_gerador(gerador_bruto)]).estabelecimentos
    estab = montar_estabelecimentos(r.movimentacoes, r.destinadores, r.geradores, cadastros).set_index("cnpj")

    gerador = estab.loc["11111111000111"]
    assert gerador["eh_gerador"] and not gerador["eh_destinador"]
    assert gerador["municipio"] == "SAO PAULO"

    aterro = estab.loc["33333333000133"]  # aparece como destinador e como gerador
    assert aterro["eh_gerador"] and aterro["eh_destinador"]

    assert len(estab) == 4


def test_montar_estabelecimentos_sem_arquivo_do_gerador(destinador_bruto):
    r = transformar_destinador(destinador_bruto)
    vazio = pd.DataFrame(columns=["cnpj", "razao_social", "uf_sigla", "municipio", "categoria_atividade",
                                  "detalhe_atividade", "situacao_cadastral"])
    estab = montar_estabelecimentos(r.movimentacoes, r.destinadores, r.geradores, vazio).set_index("cnpj")
    gerador = estab.loc["11111111000111"]
    assert gerador["situacao_cadastral"] == "Não informada"
    assert pd.isna(gerador["municipio"])
