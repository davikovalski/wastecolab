"""Testes da API contra o banco de teste (TEST_DATABASE_URL), conectando como api_leitura."""

from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import criar_app
from tests.banco_teste import URL, preparar_banco

pytestmark = pytest.mark.integracao

GERADOR = "11111111000111"
RECICLADOR = "22222222000122"


def _url_api_leitura(url: str) -> str:
    """Mesma base, mas com o usuário só leitura criado pela migration."""
    info = psycopg.conninfo.conninfo_to_dict(url)
    info.update(user="api_leitura", password="senha_teste")
    return psycopg.conninfo.make_conninfo(**{k: str(v) for k, v in info.items() if v is not None})


@pytest.fixture(scope="module")
def cliente(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    if URL is None:
        pytest.skip("defina TEST_DATABASE_URL para rodar os testes da API")
    preparar_banco(URL, tmp_path_factory.mktemp("api"))
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute("alter role api_leitura with login password 'senha_teste'")
    settings = Settings(api_database_url=_url_api_leitura(URL), cors_origins=["http://localhost:8081"])
    with TestClient(criar_app(settings)) as c:
        yield c


def test_saude(cliente):
    r = cliente.get("/v1/saude")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "ok" and corpo["dados_atualizados_em"] is not None
    assert "etag" not in r.headers


def test_lista_vazia_no_raio_pequeno(cliente):
    r = cliente.get("/v1/oportunidades", params={"raio_km": 100})
    assert r.status_code == 200
    assert r.json() == {"itens": [], "pagina": 1, "por_pagina": 20, "total": 0, "raio_km": 100}


def test_lista_com_rota(cliente):
    r = cliente.get("/v1/oportunidades", params={"raio_km": 250})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total"] == 1 and corpo["raio_km"] == 250
    item = corpo["itens"][0]
    assert item["gerador"]["cnpj"] == GERADOR
    assert item["gerador"]["municipio"] == {"id_ibge": 3550308, "nome": "São Paulo", "uf": "SP"}
    assert item["residuo"] == {"codigo": "070213", "descricao": "Resíduos de plásticos", "perigoso": False}
    assert item["operacoes_atuais"] == [{"codigo": "D5", "descricao": "Aterramentos especialmente projetados"}]
    # Sem litros/unidades informados: null, nunca 0.
    assert item["quantidade"] == {"toneladas": 15.001, "litros": None, "unidades": None}
    assert item["rotas"]["total"] == 1 and 100 < item["rotas"]["distancia_mais_proxima_km"] < 200
    assert item["localizacao"]["precisao"] == "municipio"


def test_filtros(cliente):
    assert cliente.get("/v1/oportunidades", params={"raio_km": 250, "uf": "rs"}).json()["total"] == 0
    assert cliente.get("/v1/oportunidades", params={"raio_km": 250, "uf": "SP"}).json()["total"] == 1
    perto_de_sp = {"raio_km": 250, "lat": -23.55, "lon": -46.63, "raio_local_km": 10}
    assert cliente.get("/v1/oportunidades", params=perto_de_sp).json()["total"] == 1
    longe = {**perto_de_sp, "lat": -3.1, "lon": -60.0}
    assert cliente.get("/v1/oportunidades", params=longe).json()["total"] == 0
    assert cliente.get("/v1/oportunidades", params={"raio_km": 250, "perigoso": "true"}).json()["total"] == 0


def test_pagina_alem_do_fim_mantem_total(cliente):
    r = cliente.get("/v1/oportunidades", params={"raio_km": 250, "pagina": 5})
    assert r.json()["itens"] == [] and r.json()["total"] == 1


@pytest.mark.parametrize(
    ("params", "campo"),
    [
        ({"raio_km": 30}, "raio_km"),
        ({"lat": -23.5}, "lat/lon"),
        ({"por_pagina": 500}, "por_pagina"),
        ({"codigo_residuo": "12"}, "codigo_residuo"),
        ({"ordem": "nome"}, "ordem"),
    ],
)
def test_validacao_no_formato_unico(cliente, params, campo):
    r = cliente.get("/v1/oportunidades", params=params)
    assert r.status_code == 422
    erro = r.json()["erro"]
    assert erro["codigo"] == "parametro_invalido"
    assert [d["campo"] for d in erro["detalhes"]] == [campo]


def test_detalhe_com_rotas_e_contexto(cliente):
    r = cliente.get(f"/v1/oportunidades/{GERADOR}/070213", params={"raio_km": 500})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["oportunidade"]["gerador"]["categoria_atividade"] == "Indústria de Produtos Químicos"
    assert [rota["destinador"]["cnpj"] for rota in corpo["rotas"]] == [RECICLADOR]
    rota = corpo["rotas"][0]
    assert rota["operacoes"][0]["codigo"] == "R3"
    assert rota["destinador"]["municipio"]["nome"] == "Mogi Mirim"
    assert rota["contexto_municipal"] is None  # Mogi Mirim não tem diagnóstico no exemplo
    assert {f["nome"] for f in corpo["fontes"]} >= {"IBAMA RAPP - Resíduos Sólidos"}


def test_detalhe_sem_rota_no_raio_devolve_lista_vazia(cliente):
    r = cliente.get(f"/v1/oportunidades/{GERADOR}/070213", params={"raio_km": 25})
    assert r.status_code == 200 and r.json()["rotas"] == []


def test_detalhe_inexistente(cliente):
    r = cliente.get("/v1/oportunidades/99999999000199/070213")
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "nao_encontrado"
    assert cliente.get("/v1/oportunidades/123/070213").status_code == 422


def test_contexto_municipal(cliente):
    corpo = cliente.get("/v1/municipios/3550308/contexto").json()
    assert corpo["municipio"]["nome"] == "São Paulo"
    assert corpo["contexto"]["ano_referencia"] == 2024  # declaração vigente, não a de 2022
    assert corpo["contexto"]["metas"][0]["tipo"] == "reciclagem"
    sem_diagnostico = cliente.get("/v1/municipios/3530805/contexto").json()
    assert sem_diagnostico["contexto"] is None
    assert cliente.get("/v1/municipios/9999999/contexto").status_code == 404


def test_filtros_de_residuos_e_municipios(cliente):
    residuos = cliente.get("/v1/residuos", params={"q": "plást"}).json()
    assert residuos == [{"codigo": "070213", "descricao": "Resíduos de plásticos", "perigoso": False,
                         "oportunidades": 1}]
    assert cliente.get("/v1/residuos", params={"q": "0702"}).json()[0]["codigo"] == "070213"
    assert cliente.get("/v1/residuos", params={"q": "PLASTICOS"}).json()[0]["codigo"] == "070213"
    municipios = cliente.get("/v1/municipios", params={"q": "sant ana", "uf": "rs"}).json()
    assert municipios == [{"id_ibge": 4317103, "nome": "Sant'Ana do Livramento", "uf": "RS"}]


def test_cache_etag_e_304(cliente):
    r = cliente.get("/v1/oportunidades", params={"raio_km": 250})
    etag = r.headers["etag"]
    assert r.headers["cache-control"] == "public, max-age=300"
    r2 = cliente.get("/v1/oportunidades", params={"raio_km": 250}, headers={"If-None-Match": etag})
    assert r2.status_code == 304
    outra = cliente.get("/v1/oportunidades", params={"raio_km": 500})
    assert outra.headers["etag"] != etag
    erro = cliente.get("/v1/oportunidades", params={"raio_km": 30})
    assert "etag" not in erro.headers and erro.headers["cache-control"] == "no-store"


def test_cors(cliente):
    r = cliente.get("/v1/saude", headers={"Origin": "http://localhost:8081"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:8081"


def test_rota_desconhecida(cliente):
    r = cliente.get("/v1/nao-existe")
    assert r.status_code == 404 and r.json()["erro"]["codigo"] == "nao_encontrado"


def test_banco_fora_do_ar_responde_503():
    settings = Settings(api_database_url="postgresql://ninguem@127.0.0.1:1/nada?connect_timeout=1",
                        pool_timeout_s=1.0)
    with TestClient(criar_app(settings)) as c:
        for caminho in ("/v1/saude", "/v1/oportunidades"):
            r = c.get(caminho)
            assert r.status_code == 503, caminho
            assert r.json()["erro"]["codigo"] == "banco_indisponivel"
