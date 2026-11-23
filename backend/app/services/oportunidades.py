"""Montagem das respostas a partir das linhas do banco."""

from dataclasses import replace
from decimal import Decimal
from typing import cast, get_args

from app.core.erros import nao_encontrado
from app.db.pool import Conexao
from app.repositories import consultas as repo
from app.schemas.modelos import (
    ContextoMunicipal,
    DetalheOportunidade,
    Estabelecimento,
    EstabelecimentoDetalhado,
    Fonte,
    Localizacao,
    Meta,
    Municipio,
    Operacao,
    Oportunidade,
    OportunidadeItem,
    PaginaOportunidades,
    Quantidade,
    RaioKm,
    Residuo,
    ResumoRotas,
    Rota,
    TipoMeta,
)

_TIPOS_META: frozenset[str] = frozenset(get_args(TipoMeta))


def _numero(valor: Decimal | None) -> float | None:
    return float(valor) if valor is not None else None


def _quantidade(ton: Decimal | None, litros: Decimal | None, unidades: Decimal | None) -> Quantidade:
    return Quantidade(toneladas=_numero(ton), litros=_numero(litros), unidades=_numero(unidades))


def _operacoes(codigos: list[str], descricoes: dict[str, str]) -> list[Operacao]:
    return [Operacao(codigo=c, descricao=descricoes.get(c, c)) for c in codigos]


async def _descricoes_operacoes(conn: Conexao) -> dict[str, str]:
    return {linha.codigo: linha.descricao for linha in await repo.listar_operacoes(conn)}


async def listar(
    conn: Conexao, filtros: repo.FiltrosOportunidades, pagina: int, raio_km: RaioKm
) -> PaginaOportunidades:
    linhas = await repo.listar_oportunidades(conn, filtros)
    if linhas:
        total = linhas[0].total
    elif filtros.offset > 0:
        # Página além do fim: ainda informa o total para o app mostrar a paginação certa.
        primeira = await repo.listar_oportunidades(conn, replace(filtros, limite=1, offset=0))
        total = primeira[0].total if primeira else 0
    else:
        total = 0
    descricoes = await _descricoes_operacoes(conn)
    itens = [
        OportunidadeItem(
            gerador=Estabelecimento(
                cnpj=linha.gerador_cnpj,
                razao_social=linha.razao_social,
                municipio=Municipio(id_ibge=linha.municipio_id, nome=linha.municipio_nome, uf=linha.uf_sigla),
            ),
            residuo=Residuo(codigo=linha.codigo_residuo, descricao=linha.residuo_descricao,
                            perigoso=linha.perigoso),
            ano=linha.ano,
            operacoes_atuais=_operacoes(linha.operacoes, descricoes),
            quantidade=_quantidade(linha.quantidade_ton, linha.quantidade_l, linha.quantidade_un),
            rotas=ResumoRotas(total=linha.n_rotas, distancia_mais_proxima_km=round(linha.distancia_rota_proxima_km, 1)),
            localizacao=Localizacao(lat=linha.lat, lon=linha.lon),
        )
        for linha in linhas
    ]
    return PaginaOportunidades(itens=itens, pagina=pagina, por_pagina=filtros.limite, total=total, raio_km=raio_km)


async def contextos_por_municipio(conn: Conexao, municipio_ids: list[int]) -> dict[int, ContextoMunicipal]:
    contextos, metas = await repo.contextos_municipais(conn, sorted(set(municipio_ids)))
    metas_por_municipio: dict[int, list[Meta]] = {}
    for meta in metas:
        if meta.tipo not in _TIPOS_META:
            continue
        metas_por_municipio.setdefault(meta.municipio_id, []).append(
            Meta(
                tipo=cast(TipoMeta, meta.tipo),
                valor_atual=_numero(meta.valor_atual),
                valor_meta=_numero(meta.valor_meta),
                prazo_texto=meta.prazo_texto,
                prazo_ano=meta.prazo_ano,
                programa=meta.programa,
            )
        )
    return {
        c.municipio_id: ContextoMunicipal(
            ano_referencia=c.ano_referencia,
            possui_coleta_seletiva=c.possui_coleta_seletiva,
            possui_plano_gestao=c.possui_plano_gestao,
            link_plano=c.link_plano,
            ano_ultima_versao_plano=c.ano_ultima_versao_plano,
            metas=metas_por_municipio.get(c.municipio_id, []),
        )
        for c in contextos
    }


async def detalhar(conn: Conexao, cnpj: str, codigo: str, raio_km: RaioKm) -> DetalheOportunidade:
    base = await repo.obter_oportunidade(conn, cnpj, codigo)
    if base is None:
        raise nao_encontrado("Oportunidade não encontrada para esse gerador e resíduo.")
    rotas = await repo.listar_rotas(conn, cnpj, codigo, int(raio_km))
    contextos = await contextos_por_municipio(conn, [r.municipio_id for r in rotas])
    descricoes = await _descricoes_operacoes(conn)
    fontes = await repo.listar_fontes(conn)
    residuo = Residuo(codigo=base.codigo_residuo, descricao=base.residuo_descricao, perigoso=base.perigoso)
    return DetalheOportunidade(
        oportunidade=Oportunidade(
            gerador=EstabelecimentoDetalhado(
                cnpj=base.gerador_cnpj,
                razao_social=base.razao_social,
                municipio=Municipio(id_ibge=base.municipio_id, nome=base.municipio_nome, uf=base.uf_sigla),
                categoria_atividade=base.categoria_atividade,
                detalhe_atividade=base.detalhe_atividade,
            ),
            residuo=residuo,
            ano=base.ano,
            operacoes_atuais=_operacoes(base.operacoes, descricoes),
            quantidade=_quantidade(base.quantidade_ton, base.quantidade_l, base.quantidade_un),
            localizacao=Localizacao(lat=base.lat, lon=base.lon),
        ),
        raio_km=raio_km,
        rotas=[
            Rota(
                destinador=Estabelecimento(
                    cnpj=r.destinador_cnpj,
                    razao_social=r.razao_social,
                    municipio=Municipio(id_ibge=r.municipio_id, nome=r.municipio_nome, uf=r.uf_sigla),
                ),
                distancia_km=round(r.distancia_km, 1),
                operacoes=_operacoes(r.operacoes, descricoes),
                ano_mais_recente=r.ano_mais_recente,
                quantidade_recebida=_quantidade(r.quantidade_ton, r.quantidade_l, r.quantidade_un),
                localizacao=Localizacao(lat=r.lat, lon=r.lon),
                contexto_municipal=contextos.get(r.municipio_id),
            )
            for r in rotas
        ],
        fontes=[
            Fonte(nome=f.nome, url=f.url, atualizado_na_fonte=f.atualizado_na_fonte, importado_em=f.importado_em)
            for f in fontes
        ],
    )
