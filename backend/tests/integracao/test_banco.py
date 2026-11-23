"""Teste de ponta a ponta: migrations + ETL + funções de busca.

Precisa de um PostgreSQL com PostGIS disponível em TEST_DATABASE_URL.
ATENÇÃO: os schemas `public` e `extensions` desse banco são apagados e recriados.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import psycopg
import pytest

from etl import pipelines
from tests.etl.test_municipal import _linha

pytestmark = pytest.mark.integracao

URL = os.environ.get("TEST_DATABASE_URL")
RAIZ = Path(__file__).resolve().parents[3]
MIGRATIONS = sorted((RAIZ / "supabase" / "migrations").glob("*.sql"))
ROLES_LOCAIS = RAIZ / "supabase" / "local" / "roles.sql"


@pytest.fixture
def conn(tmp_path: Path, destinador_bruto, gerador_bruto, ibge_bruto) -> Iterator[psycopg.Connection]:
    if URL is None:
        pytest.skip("defina TEST_DATABASE_URL para rodar os testes de integração")
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute("drop schema if exists public cascade")
        admin.execute("drop schema if exists extensions cascade")
        admin.execute("create schema public")
        admin.execute(ROLES_LOCAIS.read_text(encoding="utf-8"))
        for arquivo in MIGRATIONS:
            admin.execute(arquivo.read_text(encoding="utf-8"))

    ibge = tmp_path / "municipios.csv"
    ibge_bruto.to_csv(ibge, index=False)
    destinador = tmp_path / "destinador.csv"
    destinador_bruto.to_csv(destinador, sep=";", index=False)
    gerador = tmp_path / "gerador.csv"
    gerador_bruto.to_csv(gerador, sep=";", index=False)
    municipal = tmp_path / "municipal.csv"
    pd.DataFrame([_linha(**{"Município Declarante": "São Paulo", "UF Declarante": "SP"})]).to_csv(
        municipal, sep=";", index=False
    )

    with psycopg.connect(URL) as c:
        for _ in range(2):  # a carga precisa ser repetível
            pipelines.carregar_ibge(c, ibge)
            pipelines.carregar_ibama(c, destinador, gerador, None, tmp_path / "relatorios", 2)
            pipelines.carregar_municipal(c, municipal, tmp_path / "relatorios")
            c.commit()
        pipelines.atualizar_views(c)
        c.commit()
        yield c


def test_carga_repetida_nao_duplica(conn):
    assert conn.execute("select count(*) from movimentacao_residuo").fetchone() == (4,)
    assert conn.execute("select count(*) from estabelecimento").fetchone() == (4,)
    assert conn.execute("select count(*) from declaracao where vigente").fetchone() == (1,)


def test_oportunidade_so_aparece_com_rota_no_raio(conn):
    # São Paulo -> Mogi Mirim fica a ~130 km.
    assert conn.execute("select count(*) from listar_oportunidades(p_raio_km => 100)").fetchone() == (0,)
    linhas = conn.execute(
        "select gerador_cnpj, codigo_residuo, operacoes, quantidade_ton, n_rotas, total"
        " from listar_oportunidades(p_raio_km => 250)"
    ).fetchall()
    assert len(linhas) == 1
    gerador, codigo, operacoes, quantidade_ton, n_rotas, total = linhas[0]
    assert (gerador, codigo, operacoes, n_rotas, total) == ("11111111000111", "070213", ["D5"], 1, 1)
    # 15.000,5 kg -> 15,001 t (a coluna guarda 3 casas decimais, ou seja, precisão de 1 kg).
    assert float(quantidade_ton) == pytest.approx(15.001)


def test_rotas_da_oportunidade(conn):
    rotas = conn.execute(
        "select destinador_cnpj, municipio_nome, operacoes, distancia_km"
        " from rotas_da_oportunidade('11111111000111', '070213', 500)"
    ).fetchall()
    assert [r[0] for r in rotas] == ["22222222000122"]  # o reciclador do RS fica a mais de 500 km
    assert rotas[0][1] == "Mogi Mirim"
    assert rotas[0][2] == ["R3"]
    assert 100 < rotas[0][3] < 200


def test_filtros_de_uf_e_codigo(conn):
    assert conn.execute(
        "select count(*) from listar_oportunidades(p_raio_km => 250, p_uf => 'RS')"
    ).fetchone() == (0,)
    assert conn.execute(
        "select count(*) from listar_oportunidades(p_raio_km => 250, p_codigo_residuo => '070213',"
        " p_perigoso => false)"
    ).fetchone() == (1,)


def test_contexto_municipal(conn):
    linha = conn.execute(
        "select possui_plano_gestao, jsonb_array_length(metas) from v_municipio_contexto"
        " where municipio_id = 3550308"
    ).fetchone()
    assert linha == (True, 1)


def test_role_anon_so_le(conn):
    conn.execute("set role anon")
    try:
        assert conn.execute("select count(*) from listar_oportunidades(p_raio_km => 250)").fetchone() == (1,)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("delete from estabelecimento")
    finally:
        conn.rollback()
        conn.execute("reset role")
