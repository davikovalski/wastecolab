"""Cache HTTP: ETag pela data da última carga do ETL + Cache-Control.

Os dados só mudam quando o ETL roda, então o app (TanStack Query) pode reaproveitar as respostas
e revalidar barato com If-None-Match (304 sem consultar a busca).
"""

import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
from fastapi import Request, Response
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.db.pool import Conexao
from app.repositories.consultas import versao_dados

log = logging.getLogger(__name__)

_TTL_VERSAO_S = 60.0
_ROTAS_SEM_CACHE = ("/v1/saude",)


@dataclass
class VersaoDados:
    valor: datetime | None = None
    lida_em: float = field(default=-1e9)

    async def obter(self, pool: AsyncConnectionPool[Conexao]) -> datetime | None:
        if time.monotonic() - self.lida_em > _TTL_VERSAO_S:
            async with pool.connection() as conn:
                self.valor = await versao_dados(conn)
            self.lida_em = time.monotonic()
        return self.valor


def calcular_etag(versao: datetime, caminho_com_query: str) -> str:
    resumo = hashlib.sha256(f"{versao.isoformat()}|{caminho_com_query}".encode()).hexdigest()[:20]
    return f'W/"{resumo}"'


def criar_middleware_cache(
    max_age_s: int,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        caminho = request.url.path
        if request.method != "GET" or not caminho.startswith("/v1/") or caminho in _ROTAS_SEM_CACHE:
            return await call_next(request)

        versao_cache: VersaoDados = request.app.state.versao_dados
        try:
            versao = await versao_cache.obter(request.app.state.pool)
        except (PoolTimeout, psycopg.OperationalError) as exc:
            log.warning("Sem versão dos dados para o cache: %s", exc)
            versao = None
        if versao is None:
            return await call_next(request)

        etag = calcular_etag(versao, f"{caminho}?{request.url.query}")
        cabecalhos = {"ETag": etag, "Cache-Control": f"public, max-age={max_age_s}"}
        if etag in request.headers.get("if-none-match", ""):
            return Response(status_code=304, headers=cabecalhos)

        resposta = await call_next(request)
        if resposta.status_code == 200:
            resposta.headers.update(cabecalhos)
        return resposta

    return middleware
