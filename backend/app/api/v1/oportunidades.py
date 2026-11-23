"""HU1/HU2 (lista e mapa) e HU3 (detalhe)."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.core.erros import RESPOSTAS_ERRO, RespostaErro, parametro_invalido
from app.db.pool import ConexaoDep
from app.repositories.consultas import FiltrosOportunidades
from app.schemas.modelos import DetalheOportunidade, Ordem, PaginaOportunidades, RaioKm
from app.services import oportunidades as servico

router = APIRouter(prefix="/oportunidades", tags=["oportunidades"])

UF = Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$", description="Sigla da UF, ex.: SP")]
Cnpj = Annotated[str, Path(pattern=r"^\d{14}$", description="CNPJ só com dígitos")]
CodigoResiduo = Annotated[str, Path(pattern=r"^\d{6}$", description="Código da Lista Brasileira de Resíduos")]


@router.get("", response_model=PaginaOportunidades, responses=RESPOSTAS_ERRO,
            summary="Geradores que mandam resíduo para aterro e têm rota de valorização no raio")
async def listar_oportunidades(
    conn: ConexaoDep,
    raio_km: Annotated[RaioKm, Query(description="Raio das rotas a partir do gerador")] = RaioKm.KM_100,
    uf: UF = None,
    municipio_id: Annotated[int | None, Query(ge=1_000_000, le=9_999_999)] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    raio_local_km: Annotated[int, Query(ge=1, le=500, description="Área em volta de lat/lon")] = 50,
    codigo_residuo: Annotated[str | None, Query(pattern=r"^\d{6}$")] = None,
    perigoso: bool | None = None,
    ordem: Ordem = "quantidade",
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PaginaOportunidades:
    if (lat is None) != (lon is None):
        raise parametro_invalido("lat/lon", "Informe lat e lon juntos.")
    filtros = FiltrosOportunidades(
        raio_km=int(raio_km),
        uf=uf.upper() if uf else None,
        municipio_id=municipio_id,
        lat=lat,
        lon=lon,
        raio_local_km=raio_local_km,
        codigo_residuo=codigo_residuo,
        perigoso=perigoso,
        ordem=ordem,
        limite=por_pagina,
        offset=(pagina - 1) * por_pagina,
    )
    return await servico.listar(conn, filtros, pagina, raio_km)


@router.get("/{cnpj}/{codigo_residuo}", response_model=DetalheOportunidade,
            responses={404: {"model": RespostaErro, "description": "Oportunidade não encontrada"},
                       **RESPOSTAS_ERRO},
            summary="Oportunidade com os destinadores candidatos e o contexto do município de cada um")
async def detalhar_oportunidade(
    conn: ConexaoDep,
    cnpj: Cnpj,
    codigo_residuo: CodigoResiduo,
    raio_km: Annotated[RaioKm, Query()] = RaioKm.KM_100,
) -> DetalheOportunidade:
    return await servico.detalhar(conn, cnpj, codigo_residuo, raio_km)
