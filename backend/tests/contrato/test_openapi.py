"""O app gera os tipos a partir de mobile/openapi.json: o arquivo precisa acompanhar a API."""

from app.exportar_openapi import DESTINO, gerar_contrato


def test_contrato_do_app_esta_atualizado():
    assert DESTINO.read_text(encoding="utf-8") == gerar_contrato(), (
        "Contrato desatualizado: rode `python -m app.exportar_openapi` e depois `npm run gerar:api` em mobile/"
    )
