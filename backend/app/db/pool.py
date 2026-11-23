"""Pool de conexões assíncrono (psycopg 3) e dependência por requisição."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings

Conexao = AsyncConnection[tuple[object, ...]]


def criar_pool(settings: Settings) -> AsyncConnectionPool[Conexao]:
    return AsyncConnectionPool(
        conninfo=settings.api_database_url,
        min_size=settings.pool_min,
        max_size=settings.pool_max,
        timeout=settings.pool_timeout_s,
        open=False,
        # O pooler do Supabase (modo transação) não suporta prepared statements.
        kwargs={"autocommit": True, "prepare_threshold": None},
    )


async def obter_conexao(request: Request) -> AsyncIterator[Conexao]:
    pool: AsyncConnectionPool[Conexao] = request.app.state.pool
    async with pool.connection() as conexao:
        yield conexao


ConexaoDep = Annotated[Conexao, Depends(obter_conexao)]
