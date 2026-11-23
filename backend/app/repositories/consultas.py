"""Acesso ao banco: uma função por consulta, retornando linhas tipadas."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from psycopg.rows import class_row

from app.db.pool import Conexao
from etl.transform.texto import normalizar_nome


@dataclass(frozen=True)
class LinhaOportunidade:
    gerador_cnpj: str
    razao_social: str
    municipio_id: int
    municipio_nome: str
    uf_sigla: str
    codigo_residuo: str
    residuo_descricao: str
    perigoso: bool | None
    ano: int
    operacoes: list[str]
    quantidade_ton: Decimal | None
    quantidade_l: Decimal | None
    quantidade_un: Decimal | None
    n_rotas: int
    distancia_rota_proxima_km: float
    lat: float
    lon: float
    total: int


@dataclass(frozen=True)
class FiltrosOportunidades:
    raio_km: int
    uf: str | None
    municipio_id: int | None
    lat: float | None
    lon: float | None
    raio_local_km: int
    codigo_residuo: str | None
    perigoso: bool | None
    ordem: str
    limite: int
    offset: int


async def listar_oportunidades(conn: Conexao, f: FiltrosOportunidades) -> list[LinhaOportunidade]:
    async with conn.cursor(row_factory=class_row(LinhaOportunidade)) as cur:
        await cur.execute(
            """
            select * from public.listar_oportunidades(
              p_raio_km => %(raio_km)s, p_uf => %(uf)s, p_municipio_id => %(municipio_id)s,
              p_lat => %(lat)s, p_lon => %(lon)s, p_raio_local_km => %(raio_local_km)s,
              p_codigo_residuo => %(codigo_residuo)s, p_perigoso => %(perigoso)s,
              p_ordem => %(ordem)s, p_limite => %(limite)s, p_offset => %(offset)s)
            """,
            {
                "raio_km": f.raio_km, "uf": f.uf, "municipio_id": f.municipio_id, "lat": f.lat,
                "lon": f.lon, "raio_local_km": f.raio_local_km, "codigo_residuo": f.codigo_residuo,
                "perigoso": f.perigoso, "ordem": f.ordem, "limite": f.limite, "offset": f.offset,
            },
        )
        return await cur.fetchall()


@dataclass(frozen=True)
class LinhaOportunidadeDetalhe:
    gerador_cnpj: str
    razao_social: str
    categoria_atividade: str | None
    detalhe_atividade: str | None
    municipio_id: int
    municipio_nome: str
    uf_sigla: str
    codigo_residuo: str
    residuo_descricao: str
    perigoso: bool | None
    ano: int
    operacoes: list[str]
    quantidade_ton: Decimal | None
    quantidade_l: Decimal | None
    quantidade_un: Decimal | None
    lat: float
    lon: float


async def obter_oportunidade(conn: Conexao, cnpj: str, codigo: str) -> LinhaOportunidadeDetalhe | None:
    async with conn.cursor(row_factory=class_row(LinhaOportunidadeDetalhe)) as cur:
        await cur.execute(
            """
            select o.gerador_cnpj, e.razao_social, e.categoria_atividade, e.detalhe_atividade,
                   o.municipio_id, mu.nome as municipio_nome, mu.uf_sigla,
                   o.codigo_residuo, cr.descricao as residuo_descricao, cr.perigoso,
                   o.ano, o.operacoes::text[] as operacoes,
                   o.quantidade_ton, o.quantidade_l, o.quantidade_un,
                   extensions.st_y(o.geom::extensions.geometry) as lat,
                   extensions.st_x(o.geom::extensions.geometry) as lon
            from public.mv_oportunidade o
            join public.estabelecimento e on e.cnpj = o.gerador_cnpj
            join public.municipio mu on mu.id_ibge = o.municipio_id
            join public.codigo_residuo cr on cr.codigo = o.codigo_residuo
            where o.gerador_cnpj = %s and o.codigo_residuo = %s
            """,
            (cnpj, codigo),
        )
        return await cur.fetchone()


@dataclass(frozen=True)
class LinhaRota:
    destinador_cnpj: str
    razao_social: str
    municipio_id: int
    municipio_nome: str
    uf_sigla: str
    distancia_km: float
    operacoes: list[str]
    ano_mais_recente: int
    quantidade_ton: Decimal | None
    quantidade_l: Decimal | None
    quantidade_un: Decimal | None
    lat: float
    lon: float


async def listar_rotas(conn: Conexao, cnpj: str, codigo: str, raio_km: int) -> list[LinhaRota]:
    async with conn.cursor(row_factory=class_row(LinhaRota)) as cur:
        await cur.execute(
            """
            select destinador_cnpj, razao_social, municipio_id, municipio_nome, uf_sigla, distancia_km,
                   operacoes::text[] as operacoes, ano_mais_recente, quantidade_ton, quantidade_l,
                   quantidade_un, lat, lon
            from public.rotas_da_oportunidade(%s, %s, %s)
            """,
            (cnpj, codigo, raio_km),
        )
        return await cur.fetchall()


@dataclass(frozen=True)
class LinhaContexto:
    municipio_id: int
    ano_referencia: int
    possui_coleta_seletiva: bool
    possui_plano_gestao: bool
    link_plano: str | None
    ano_ultima_versao_plano: int | None


@dataclass(frozen=True)
class LinhaMeta:
    municipio_id: int
    tipo: str
    valor_atual: Decimal | None
    valor_meta: Decimal | None
    prazo_texto: str | None
    prazo_ano: int | None
    programa: str | None


async def contextos_municipais(
    conn: Conexao, municipio_ids: list[int]
) -> tuple[list[LinhaContexto], list[LinhaMeta]]:
    """Declaração vigente e metas de vários municípios em duas consultas."""
    if not municipio_ids:
        return [], []
    async with conn.cursor(row_factory=class_row(LinhaContexto)) as cur:
        await cur.execute(
            """
            select municipio_id, ano_referencia, possui_coleta_seletiva, possui_plano_gestao, link_plano,
                   ano_ultima_versao_plano
            from public.declaracao
            where vigente and municipio_id = any(%s)
            """,
            (municipio_ids,),
        )
        contextos = await cur.fetchall()
    async with conn.cursor(row_factory=class_row(LinhaMeta)) as cur:
        await cur.execute(
            """
            select d.municipio_id, m.tipo::text as tipo, m.valor_atual, m.valor_meta, m.prazo_texto,
                   m.prazo_ano, m.programa
            from public.meta m
            join public.declaracao d on d.id = m.declaracao_id and d.vigente
            where d.municipio_id = any(%s)
            order by d.municipio_id, m.tipo, m.id
            """,
            (municipio_ids,),
        )
        metas = await cur.fetchall()
    return contextos, metas


@dataclass(frozen=True)
class LinhaOperacao:
    codigo: str
    descricao: str


async def listar_operacoes(conn: Conexao) -> list[LinhaOperacao]:
    async with conn.cursor(row_factory=class_row(LinhaOperacao)) as cur:
        await cur.execute("select codigo::text as codigo, descricao from public.operacao_destinacao")
        return await cur.fetchall()


@dataclass(frozen=True)
class LinhaResiduoBusca:
    codigo: str
    descricao: str
    perigoso: bool | None
    oportunidades: int


async def buscar_residuos(
    conn: Conexao, termo: str | None, perigoso: bool | None, limite: int
) -> list[LinhaResiduoBusca]:
    """Busca por prefixo do código ou por trecho da descrição, ignorando acentos e maiúsculas."""
    termo_sem_acento = normalizar_nome(termo)
    async with conn.cursor(row_factory=class_row(LinhaResiduoBusca)) as cur:
        await cur.execute(
            """
            select cr.codigo, cr.descricao, cr.perigoso, count(*) as oportunidades
            from public.codigo_residuo cr
            join public.mv_oportunidade o on o.codigo_residuo = cr.codigo
            where (%(termo)s::text is null
                   or cr.codigo like %(prefixo)s
                   or translate(lower(cr.descricao), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc')
                      like %(contem)s)
              and (%(perigoso)s::boolean is null or cr.perigoso = %(perigoso)s)
            group by cr.codigo, cr.descricao, cr.perigoso
            order by count(*) desc, cr.codigo
            limit %(limite)s
            """,
            {
                "termo": termo,
                "prefixo": f"{termo}%" if termo else None,
                "contem": f"%{termo_sem_acento}%" if termo_sem_acento else None,
                "perigoso": perigoso,
                "limite": limite,
            },
        )
        return await cur.fetchall()


@dataclass(frozen=True)
class LinhaMunicipio:
    id_ibge: int
    nome: str
    uf_sigla: str


async def buscar_municipios(
    conn: Conexao, uf: str | None, termo_normalizado: str | None, limite: int
) -> list[LinhaMunicipio]:
    async with conn.cursor(row_factory=class_row(LinhaMunicipio)) as cur:
        await cur.execute(
            """
            select id_ibge, nome, uf_sigla
            from public.municipio
            where (%(uf)s::text is null or uf_sigla = %(uf)s)
              and (%(termo)s::text is null or nome_normalizado like %(contem)s)
            order by (nome_normalizado like %(prefixo)s) desc, nome, uf_sigla
            limit %(limite)s
            """,
            {
                "uf": uf,
                "termo": termo_normalizado,
                "contem": f"%{termo_normalizado}%" if termo_normalizado else None,
                "prefixo": f"{termo_normalizado}%" if termo_normalizado else "",
                "limite": limite,
            },
        )
        return await cur.fetchall()


async def obter_municipio(conn: Conexao, id_ibge: int) -> LinhaMunicipio | None:
    async with conn.cursor(row_factory=class_row(LinhaMunicipio)) as cur:
        await cur.execute("select id_ibge, nome, uf_sigla from public.municipio where id_ibge = %s", (id_ibge,))
        return await cur.fetchone()


@dataclass(frozen=True)
class LinhaFonte:
    nome: str
    url: str | None
    atualizado_na_fonte: date | None
    importado_em: datetime


async def listar_fontes(conn: Conexao) -> list[LinhaFonte]:
    async with conn.cursor(row_factory=class_row(LinhaFonte)) as cur:
        await cur.execute("select nome, url, atualizado_na_fonte, importado_em from public.fonte_dado order by nome")
        return await cur.fetchall()


async def versao_dados(conn: Conexao) -> datetime | None:
    """Data da última carga do ETL: base do ETag e de `dados_atualizados_em`."""
    async with conn.cursor() as cur:
        await cur.execute("select max(importado_em) from public.fonte_dado")
        linha = await cur.fetchone()
    valor = linha[0] if linha else None
    return valor if isinstance(valor, datetime) else None
