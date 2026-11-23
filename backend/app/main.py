"""Aplicação FastAPI do Waste Colab (somente leitura).

Rodar localmente:  uvicorn app.main:criar_app --factory --reload
(a fábrica evita ler a configuração no import, o que facilita os testes)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import catalogos, oportunidades
from app.core.cache import VersaoDados, criar_middleware_cache
from app.core.config import Settings, obter_settings
from app.core.erros import registrar_handlers
from app.db.pool import criar_pool


def criar_app(settings: Settings | None = None) -> FastAPI:
    ajustes = settings or obter_settings()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        pool = criar_pool(ajustes)
        # wait=False: a API sobe mesmo com o banco fora do ar e responde 503 até ele voltar.
        await pool.open(wait=False)
        app.state.pool = pool
        app.state.versao_dados = VersaoDados()
        try:
            yield
        finally:
            await pool.close()

    app = FastAPI(
        title="Waste Colab API",
        version="1.0.0",
        description="Oportunidades de valorização de resíduos industriais (IBAMA RAPP + diagnóstico municipal).",
        lifespan=ciclo_de_vida,
    )
    registrar_handlers(app)
    app.middleware("http")(criar_middleware_cache(ajustes.cache_max_age_s))
    if ajustes.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ajustes.cors_origins,
            allow_methods=["GET"],
            allow_headers=["If-None-Match"],
            expose_headers=["ETag"],
        )
    app.include_router(catalogos.router, prefix="/v1")
    app.include_router(oportunidades.router, prefix="/v1")
    return app

