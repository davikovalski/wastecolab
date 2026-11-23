"""Linhas de exemplo no formato original dos arquivos do IBAMA e do IBGE."""

import pandas as pd
import pytest

CNPJ_GERADOR = "11.111.111/0001-11"
CNPJ_RECICLADOR = "22.222.222/0001-22"
CNPJ_ATERRO = "33.333.333/0001-33"
CNPJ_RECICLADOR_LONGE = "44.444.444/0001-44"


def linha_destinador(
    destinador: str,
    razao_destinador: str,
    estado: str,
    municipio: str,
    gerador: str,
    codigo: str,
    ano: str,
    quantidade: str,
    unidade: str,
    tipo: str,
    situacao: str = "Ativa",
) -> dict[str, str]:
    return {
        "CNPJ do destinador": destinador,
        "Razão Social do destinador": razao_destinador,
        "Estado": estado,
        "Município": municipio,
        "Código da Categoria": "17",
        "Categoria de Atividade": "Serviços de Utilidade",
        "Código do Detalhe": "64",
        "Detalhe": "Disposição de resíduos especiais",
        "CNPJ do gerador do resíduo": gerador,
        "Raz soc do gerador do resíduo": "GERADORA EXEMPLO LTDA",
        "Cód. Resíduo": codigo,
        "Desc. Resíduo": "Aparas de plástico",
        "Ano - destinação": ano,
        "Quant. destinada": quantidade,
        "Unidade": unidade,
        "Tipo de destinação": tipo,
        "Situação Cadastral": situacao,
    }


def criar_destinador_bruto() -> pd.DataFrame:
    aterro = "D5 - Aterramentos especialmente projetados"
    reciclagem = "R3 - Reciclagem/reaproveitamento de substâncias orgânicas que não sejam usadas como solventes"
    linhas = [
        # Gerador manda 070213 para aterro em 2024 (duas linhas que somam).
        linha_destinador(CNPJ_ATERRO, "ATERRO SA", "SAO PAULO", "SAO PAULO", CNPJ_GERADOR, "070213",
                         "2024", "10.000,00", "kilogramas (kg)", aterro),
        linha_destinador(CNPJ_ATERRO, "ATERRO SA", "SAO PAULO", "SAO PAULO", CNPJ_GERADOR, "070213",
                         "2024", "5.000,50", "kilogramas (kg)", aterro),
        # Ano antigo: o gerador já valorizou esse resíduo em 2020 (não muda a oportunidade de 2024).
        linha_destinador(CNPJ_RECICLADOR, "RECICLA LTDA", "SAO PAULO", "MOJI MIRIM", CNPJ_GERADOR, "070213",
                         "2020", "1,00", "kilogramas (kg)", reciclagem),
        # Outro gerador alimenta o reciclador próximo (rota) e o reciclador distante.
        linha_destinador(CNPJ_RECICLADOR, "RECICLA LTDA", "SAO PAULO", "MOJI MIRIM", CNPJ_ATERRO, "070213",
                         "2024", "2.000,00", "kilogramas (kg)", reciclagem),
        linha_destinador(CNPJ_RECICLADOR_LONGE, "RECICLA SUL", "RIO GRANDE DO SUL",
                         "SANTANA DO LIVRAMENTO", CNPJ_ATERRO, "070213", "2023", "300,00", "Litro (L)",
                         reciclagem),
        # Linha inválida: gerador com CPF.
        linha_destinador(CNPJ_ATERRO, "ATERRO SA", "SAO PAULO", "SAO PAULO", "123.456.789-00", "070213",
                         "2024", "1,00", "kilogramas (kg)", aterro),
    ]
    return pd.DataFrame(linhas, dtype="string")


def criar_gerador_bruto() -> pd.DataFrame:
    base = {
        "Código da Categoria": "3",
        "Categoria de Atividade": "Indústria de Produtos Químicos",
        "Código do Detalhe": "1",
        "Detalhe": "Fabricação de plásticos",
        "Unidade": "kilogramas",
        "Quantidade Gerada": "1,00",
    }
    linhas = [
        {**base, "CNPJ do gerador": CNPJ_GERADOR, "Razão Social do gerador": "GERADORA ANTIGA",
         "Estado": "SAO PAULO", "Município": "SAO PAULO", "Ano da geração": "2019",
         "Cód. Resíduo": "070213", "Tipo de Resíduo": "Resíduos de plásticos",
         "Classificação Resíduo": "", "Situação Cadastral": "Ativa"},
        {**base, "CNPJ do gerador": CNPJ_GERADOR, "Razão Social do gerador": "GERADORA EXEMPLO LTDA",
         "Estado": "SAO PAULO", "Município": "SAO PAULO", "Ano da geração": "2024",
         "Cód. Resíduo": "070213", "Tipo de Resíduo": "Resíduos de plásticos",
         "Classificação Resíduo": "Não Perigoso", "Situação Cadastral": "Ativa"},
        {**base, "CNPJ do gerador": CNPJ_ATERRO, "Razão Social do gerador": "ATERRO SA",
         "Estado": "SAO PAULO", "Município": "SAO PAULO", "Ano da geração": "2024",
         "Cód. Resíduo": "200301", "Tipo de Resíduo": "Outros resíduos urbanos",
         "Classificação Resíduo": "Não Perigoso", "Situação Cadastral": "Ativa"},
    ]
    return pd.DataFrame(linhas, dtype="string")


def criar_ibge_bruto() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "codigo_ibge": [3550308, 3530805, 4317103],
            "nome": ["São Paulo", "Mogi Mirim", "Sant'Ana do Livramento"],
            "latitude": [-23.5329, -22.4332, -30.8773],
            "longitude": [-46.6395, -46.9532, -55.5392],
            "codigo_uf": [35, 35, 43],
        }
    )


@pytest.fixture
def destinador_bruto() -> pd.DataFrame:
    return criar_destinador_bruto()


@pytest.fixture
def gerador_bruto() -> pd.DataFrame:
    return criar_gerador_bruto()


@pytest.fixture
def ibge_bruto() -> pd.DataFrame:
    return criar_ibge_bruto()
