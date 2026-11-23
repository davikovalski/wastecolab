"""Banco de teste compartilhado pelos testes de integração e da API.

Precisa de um PostgreSQL com PostGIS em TEST_DATABASE_URL.
ATENÇÃO: os schemas `public` e `extensions` desse banco são apagados e recriados.
"""

import os
from pathlib import Path

import pandas as pd
import psycopg

from etl import pipelines
from tests.conftest import criar_destinador_bruto, criar_gerador_bruto, criar_ibge_bruto
from tests.etl.test_municipal import _linha

URL = os.environ.get("TEST_DATABASE_URL")
RAIZ = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((RAIZ / "supabase" / "migrations").glob("*.sql"))
ROLES_LOCAIS = RAIZ / "supabase" / "local" / "roles.sql"


def preparar_banco(url: str, tmp_path: Path) -> None:
    """Recria os schemas, aplica as migrations e carrega os dados de exemplo (duas vezes)."""
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute("drop schema if exists public cascade")
        admin.execute("drop schema if exists extensions cascade")
        admin.execute("create schema public")
        admin.execute(ROLES_LOCAIS.read_text(encoding="utf-8"))
        for arquivo in MIGRATIONS:
            admin.execute(arquivo.read_text(encoding="utf-8"))

    ibge = tmp_path / "municipios.csv"
    criar_ibge_bruto().to_csv(ibge, index=False)
    destinador = tmp_path / "destinador.csv"
    criar_destinador_bruto().to_csv(destinador, sep=";", index=False)
    gerador = tmp_path / "gerador.csv"
    criar_gerador_bruto().to_csv(gerador, sep=";", index=False)
    municipal = tmp_path / "municipal_2025.csv"
    pd.DataFrame([_linha(**{"Município Declarante": "São Paulo", "UF Declarante": "SP"})]).to_csv(
        municipal, sep=";", index=False
    )
    # Edição antiga (formato de 2022): outra declaração do mesmo município, entregue antes.
    municipal_2022 = tmp_path / "municipal_2022.csv"
    antiga = _linha(**{"Declaração": "9.001", "Ano": "2022", "Ano Referencia": "2021",
                       "Data Entrega": "20/04/2022", "Município Declarante": "São Paulo",
                       "UF Declarante": "SP", "Possui Plano de Gestão": "Não", "Massa (TON)": "1.681,20"})
    pd.DataFrame([antiga]).to_csv(municipal_2022, sep=";", index=False, encoding="utf-8-sig")

    with psycopg.connect(url) as c:
        for _ in range(2):  # a carga precisa ser repetível
            pipelines.carregar_ibge(c, ibge)
            pipelines.carregar_ibama(c, destinador, gerador, None, tmp_path / "relatorios", 2)
            # A edição mais nova é carregada primeiro de propósito: a vigente não depende da ordem.
            pipelines.carregar_municipais(c, [municipal, municipal_2022], tmp_path / "relatorios")
            c.commit()
        pipelines.atualizar_views(c)
        c.commit()
