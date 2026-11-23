"""Filtros do app (resíduos e municípios), contexto municipal e saúde."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.core.erros import RESPOSTAS_ERRO, RespostaErro, nao_encontrado
from app.db.pool import ConexaoDep
from app.repositories import consultas as repo
from app.schemas.modelos import Municipio, ResiduoBusca, RespostaContexto, Saude
from app.services.oportunidades import contextos_por_municipio
from etl.transform.texto import normalizar_nome

router = APIRouter()


@router.get("/saude", response_model=Saude, responses=RESPOSTAS_ERRO, tags=["saude"])
async def saude(conn: ConexaoDep) -> Saude:
    return Saude(status="ok", banco="ok", dados_atualizados_em=await repo.versao_dados(conn))


@router.get("/residuos", response_model=list[ResiduoBusca], responses=RESPOSTAS_ERRO, tags=["filtros"],
            summary="Resíduos que têm oportunidade, por código ou descrição")
async def buscar_residuos(
    conn: ConexaoDep,
    q: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    perigoso: bool | None = None,
    limite: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[ResiduoBusca]:
    linhas = await repo.buscar_residuos(conn, q.strip() if q else None, perigoso, limite)
    return [
        ResiduoBusca(codigo=r.codigo, descricao=r.descricao, perigoso=r.perigoso, oportunidades=r.oportunidades)
        for r in linhas
    ]


@router.get("/municipios", response_model=list[Municipio], responses=RESPOSTAS_ERRO, tags=["filtros"])
async def buscar_municipios(
    conn: ConexaoDep,
    uf: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    limite: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[Municipio]:
    linhas = await repo.buscar_municipios(conn, uf.upper() if uf else None, normalizar_nome(q), limite)
    return [Municipio(id_ibge=m.id_ibge, nome=m.nome, uf=m.uf_sigla) for m in linhas]


@router.get("/municipios/{id_ibge}/contexto", response_model=RespostaContexto,
            responses={404: {"model": RespostaErro, "description": "Município inexistente"}, **RESPOSTAS_ERRO},
            tags=["municipios"])
async def contexto_municipio(
    conn: ConexaoDep, id_ibge: Annotated[int, Path(ge=1_000_000, le=9_999_999)]
) -> RespostaContexto:
    municipio = await repo.obter_municipio(conn, id_ibge)
    if municipio is None:
        raise nao_encontrado("Município não encontrado.")
    contextos = await contextos_por_municipio(conn, [id_ibge])
    return RespostaContexto(
        municipio=Municipio(id_ibge=municipio.id_ibge, nome=municipio.nome, uf=municipio.uf_sigla),
        contexto=contextos.get(id_ibge),
    )
