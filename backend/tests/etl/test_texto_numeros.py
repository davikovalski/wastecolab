import pandas as pd
import pytest

from etl.transform.numeros import inteiro_ou_nulo, numero_br, numero_ponto
from etl.transform.texto import limpar_cnpj, limpar_texto, normalizar_nome


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Sant'Ana do Livramento", "sant ana do livramento"),
        ("SAO PAULO", "sao paulo"),
        ("  São  João d'Aliança ", "sao joao d alianca"),
        ("Não Perigoso", "nao perigoso"),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_normalizar_nome(entrada, esperado):
    assert normalizar_nome(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("00.001.180/0001-26", "00001180000126"),
        ("00001180000126", "00001180000126"),
        ("123.456.789-00", None),  # CPF não é aceito
        ("", None),
        (None, None),
    ],
)
def test_limpar_cnpj(entrada, esperado):
    assert limpar_cnpj(entrada) == esperado


def test_limpar_texto_troca_vazio_por_nulo():
    resultado = limpar_texto(pd.Series(["  abc ", "", "   ", None]))
    assert resultado.iloc[0] == "abc"
    assert resultado.iloc[1:].isna().all()


def test_numero_br():
    resultado = numero_br(pd.Series(["30.000,00", "1.956,00", "150,5", "0,001", "abc", None]))
    assert resultado.tolist()[:4] == [30000.0, 1956.0, 150.5, 0.001]
    assert resultado.iloc[4:].isna().all()


def test_numero_ponto():
    resultado = numero_ponto(pd.Series(["226.3", "10", " 3241 ", "x"]))
    assert resultado.tolist()[:3] == [226.3, 10.0, 3241.0]
    assert pd.isna(resultado.iloc[3])


def test_inteiro_ou_nulo_descarta_fora_do_intervalo():
    resultado = inteiro_ou_nulo(pd.Series(["4", "04", "2016", "x", None]), 0, 30)
    assert resultado.tolist()[:2] == [4, 4]
    assert resultado.iloc[2:].isna().all()
