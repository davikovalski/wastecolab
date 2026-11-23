"""Erros da API num formato único: {"erro": {"codigo", "mensagem", "detalhes"}}."""

import logging
from typing import Literal

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg_pool import PoolTimeout
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

CodigoErro = Literal["nao_encontrado", "parametro_invalido", "banco_indisponivel", "erro_interno"]


class DetalheCampo(BaseModel):
    campo: str
    mensagem: str


class CorpoErro(BaseModel):
    codigo: CodigoErro
    mensagem: str
    detalhes: list[DetalheCampo] | None = None


class RespostaErro(BaseModel):
    erro: CorpoErro


class ErroApi(Exception):
    def __init__(
        self, status: int, codigo: CodigoErro, mensagem: str, detalhes: list[DetalheCampo] | None = None
    ) -> None:
        super().__init__(mensagem)
        self.status = status
        self.corpo = CorpoErro(codigo=codigo, mensagem=mensagem, detalhes=detalhes)


def nao_encontrado(mensagem: str) -> ErroApi:
    return ErroApi(404, "nao_encontrado", mensagem)


def parametro_invalido(campo: str, mensagem: str) -> ErroApi:
    return ErroApi(422, "parametro_invalido", "Parâmetros inválidos.",
                   [DetalheCampo(campo=campo, mensagem=mensagem)])


def _resposta(status: int, corpo: CorpoErro) -> JSONResponse:
    return JSONResponse(status_code=status, content=RespostaErro(erro=corpo).model_dump(mode="json"),
                        headers={"Cache-Control": "no-store"})


# Respostas documentadas no OpenAPI de todas as rotas.
RESPOSTAS_ERRO: dict[int | str, dict[str, object]] = {
    422: {"model": RespostaErro, "description": "Parâmetros inválidos"},
    503: {"model": RespostaErro, "description": "Banco indisponível"},
    500: {"model": RespostaErro, "description": "Erro interno"},
}


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroApi)
    async def _erro_api(_: Request, exc: ErroApi) -> JSONResponse:
        return _resposta(exc.status, exc.corpo)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError) -> JSONResponse:
        detalhes = [
            DetalheCampo(
                campo=".".join(str(parte) for parte in erro.get("loc", ()) if parte not in ("query", "path")),
                mensagem=str(erro.get("msg", "")),
            )
            for erro in exc.errors()
        ]
        return _resposta(422, CorpoErro(codigo="parametro_invalido", mensagem="Parâmetros inválidos.",
                                        detalhes=detalhes))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _resposta(404, CorpoErro(codigo="nao_encontrado", mensagem="Recurso não encontrado."))
        return _resposta(exc.status_code, CorpoErro(codigo="erro_interno", mensagem=str(exc.detail)))

    @app.exception_handler(PoolTimeout)
    async def _pool(_: Request, exc: PoolTimeout) -> JSONResponse:
        log.error("Sem conexão disponível com o banco: %s", exc)
        return _resposta(503, CorpoErro(codigo="banco_indisponivel",
                                        mensagem="Banco de dados indisponível. Tente novamente."))

    @app.exception_handler(psycopg.OperationalError)
    async def _operacional(_: Request, exc: psycopg.OperationalError) -> JSONResponse:
        log.error("Falha de conexão com o banco: %s", exc)
        return _resposta(503, CorpoErro(codigo="banco_indisponivel",
                                        mensagem="Banco de dados indisponível. Tente novamente."))

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Erro não tratado", exc_info=exc)
        return _resposta(500, CorpoErro(codigo="erro_interno", mensagem="Erro interno."))
