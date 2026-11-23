"""Orquestração das cargas. Cada pipeline roda numa transação e pode ser repetido."""

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
from psycopg import Connection

from etl import config
from etl.extractors import fontes
from etl.load import copiar_para_temporaria, ler_tabela, registrar_fonte, upsert
from etl.reports import salvar_relatorio
from etl.transform.ibama import (
    LoteGerador,
    consolidar_lotes_gerador,
    transformar_destinador,
    transformar_lote_gerador,
)
from etl.transform.localidades import preparar_municipios_ibge, resolver_municipio
from etl.transform.municipal import transformar_diagnostico

log = logging.getLogger(__name__)

Conexao = Connection[tuple[object, ...]]


@dataclass(frozen=True)
class ResumoCarga:
    nome: str
    contagens: dict[str, int]

    def __str__(self) -> str:
        itens = ", ".join(f"{k}={v}" for k, v in self.contagens.items())
        return f"{self.nome}: {itens}"


def _municipios(conn: Conexao) -> pd.DataFrame:
    return ler_tabela(conn, "select id_ibge, nome_normalizado, uf_sigla from public.municipio")


# --------------------------------------------------------------------------- IBGE

def carregar_ibge(conn: Conexao, arquivo: Path) -> ResumoCarga:
    municipios = preparar_municipios_ibge(fontes.ler_municipios_ibge(arquivo))
    colunas = ["id_ibge", "nome", "nome_normalizado", "uf_sigla", "latitude", "longitude"]
    temporaria = copiar_para_temporaria(
        conn, "municipio", municipios, colunas,
        tipos_extras={"latitude": "double precision", "longitude": "double precision"},
    )
    with conn.cursor() as cur:
        cur.execute(
            f"""
            insert into public.municipio (id_ibge, nome, nome_normalizado, uf_sigla, geom)
            select id_ibge, nome, nome_normalizado, uf_sigla,
                   extensions.st_setsrid(extensions.st_makepoint(longitude, latitude), 4326)::extensions.geography
            from {temporaria}
            on conflict (id_ibge) do update
              set nome = excluded.nome,
                  nome_normalizado = excluded.nome_normalizado,
                  uf_sigla = excluded.uf_sigla,
                  geom = excluded.geom
            """
        )
        total = cur.rowcount
    return ResumoCarga("ibge", {"municipios": total})


# --------------------------------------------------------------------------- IBAMA

def _cadastros_gerador(arquivo: Path | None, tamanho_lote: int) -> LoteGerador:
    if arquivo is None:
        vazio = pd.DataFrame(columns=["cnpj", "razao_social", "uf_sigla", "municipio",
                                      "categoria_atividade", "detalhe_atividade", "situacao_cadastral"])
        return LoteGerador(estabelecimentos=vazio,
                           codigos=pd.DataFrame(columns=["codigo", "descricao", "perigoso"]))
    lotes: list[LoteGerador] = []
    for numero, lote in enumerate(fontes.ler_gerador_em_lotes(arquivo, tamanho_lote), start=1):
        lotes.append(transformar_lote_gerador(lote))
        log.info("Arquivo do gerador: lote %d processado", numero)
    return consolidar_lotes_gerador(lotes)


def montar_estabelecimentos(
    movimentacoes: pd.DataFrame,
    destinadores: pd.DataFrame,
    geradores_minimos: pd.DataFrame,
    cadastros_gerador: pd.DataFrame,
) -> pd.DataFrame:
    """Um registro por CNPJ envolvido nas movimentações.

    Prioridade dos dados cadastrais: arquivo do gerador > arquivo do destinador > só a razão social.
    """
    cnpjs_geradores = set(movimentacoes["gerador_cnpj"])
    cnpjs_destinadores = set(movimentacoes["destinador_cnpj"])
    minimos = geradores_minimos.assign(
        uf_sigla=None, municipio=None, categoria_atividade=None, detalhe_atividade=None,
        situacao_cadastral="Não informada",
    )
    colunas = ["cnpj", "razao_social", "uf_sigla", "municipio", "categoria_atividade",
               "detalhe_atividade", "situacao_cadastral"]
    candidatos = pd.concat(
        [cadastros_gerador[colunas].assign(_prioridade=0),
         destinadores[colunas].assign(_prioridade=1),
         minimos[colunas].assign(_prioridade=2)],
        ignore_index=True,
    )
    candidatos = candidatos[candidatos["cnpj"].isin(cnpjs_geradores | cnpjs_destinadores)]
    estabelecimentos = (
        candidatos.sort_values("_prioridade").drop_duplicates("cnpj", keep="first")
        .drop(columns=["_prioridade"]).reset_index(drop=True)
    )
    estabelecimentos["situacao_cadastral"] = estabelecimentos["situacao_cadastral"].fillna("Não informada")
    estabelecimentos["eh_gerador"] = estabelecimentos["cnpj"].isin(cnpjs_geradores)
    estabelecimentos["eh_destinador"] = estabelecimentos["cnpj"].isin(cnpjs_destinadores)
    return estabelecimentos


def carregar_ibama(
    conn: Conexao,
    arquivo_destinador: Path,
    arquivo_gerador: Path | None,
    atualizado_na_fonte: date | None,
    relatorios_dir: Path,
    tamanho_lote: int,
) -> ResumoCarga:
    destinador = transformar_destinador(fontes.ler_destinador(arquivo_destinador))
    cadastros = _cadastros_gerador(arquivo_gerador, tamanho_lote)

    estabelecimentos = montar_estabelecimentos(
        destinador.movimentacoes, destinador.destinadores, destinador.geradores, cadastros.estabelecimentos
    )
    estabelecimentos["municipio_id"] = resolver_municipio(
        estabelecimentos["municipio"], estabelecimentos["uf_sigla"], _municipios(conn)
    )
    sem_municipio = estabelecimentos[estabelecimentos["municipio_id"].isna()]
    salvar_relatorio(relatorios_dir, "ibama_estabelecimentos_sem_municipio", sem_municipio)
    salvar_relatorio(relatorios_dir, "ibama_linhas_rejeitadas", destinador.rejeitadas)

    codigos: pd.DataFrame = (
        pd.concat([cadastros.codigos.assign(_p=0), destinador.codigos.assign(perigoso=None, _p=1)],
                  ignore_index=True)
        .sort_values("_p").drop_duplicates("codigo", keep="first").drop(columns=["_p"])
    )
    codigos["perigoso"] = codigos["perigoso"].astype("boolean")

    fonte_id = registrar_fonte(conn, config.FONTE_IBAMA, config.URL_IBAMA_DESTINADOR, atualizado_na_fonte)
    upsert(conn, "operacao_destinacao", destinador.operacoes, ["codigo", "descricao", "categoria"],
           ["codigo"])
    n_codigos = upsert(
        conn, "codigo_residuo", codigos, ["codigo", "descricao", "perigoso"], ["codigo"],
        atualizar={"descricao": "excluded.descricao",
                   "perigoso": "coalesce(excluded.perigoso, t.perigoso)"},
    )
    n_estab = upsert(
        conn, "estabelecimento", estabelecimentos,
        ["cnpj", "razao_social", "municipio_id", "categoria_atividade", "detalhe_atividade",
         "situacao_cadastral", "eh_gerador", "eh_destinador"],
        ["cnpj"],
        atualizar={
            "razao_social": "excluded.razao_social",
            "municipio_id": "coalesce(excluded.municipio_id, t.municipio_id)",
            "categoria_atividade": "coalesce(excluded.categoria_atividade, t.categoria_atividade)",
            "detalhe_atividade": "coalesce(excluded.detalhe_atividade, t.detalhe_atividade)",
            "situacao_cadastral": "excluded.situacao_cadastral",
            "eh_gerador": "t.eh_gerador or excluded.eh_gerador",
            "eh_destinador": "t.eh_destinador or excluded.eh_destinador",
        },
    )

    movimentacoes = destinador.movimentacoes.assign(fonte_id=fonte_id)
    with conn.cursor() as cur:
        cur.execute("delete from public.movimentacao_residuo where fonte_id = %s", (fonte_id,))
    n_mov = upsert(
        conn, "movimentacao_residuo", movimentacoes,
        ["gerador_cnpj", "destinador_cnpj", "codigo_residuo", "operacao", "ano", "quantidade",
         "unidade", "fonte_id"],
        ["gerador_cnpj", "destinador_cnpj", "codigo_residuo", "operacao", "ano", "unidade"],
    )
    return ResumoCarga("ibama", {
        "movimentacoes": n_mov,
        "estabelecimentos": n_estab,
        "estabelecimentos_sem_municipio": len(sem_municipio),
        "codigos_residuo": n_codigos,
        "linhas_rejeitadas": len(destinador.rejeitadas),
    })


# --------------------------------------------------------------------------- Diagnóstico municipal

def _mapa_ids(conn: Conexao, tabela: str) -> dict[str, int]:
    tabela_df = ler_tabela(conn, f"select id, descricao from public.{tabela}")
    return dict(zip(tabela_df["descricao"], tabela_df["id"].astype(int), strict=True))


def carregar_municipal(conn: Conexao, arquivo: Path, relatorios_dir: Path) -> ResumoCarga:
    r = transformar_diagnostico(fontes.ler_diagnostico_municipal(arquivo))
    declaracoes = r.declaracoes.copy()
    declaracoes["municipio_id"] = resolver_municipio(
        declaracoes["municipio"], declaracoes["uf_sigla"], _municipios(conn)
    )
    sem_municipio = declaracoes[declaracoes["municipio_id"].isna()]
    salvar_relatorio(relatorios_dir, f"municipal_sem_municipio_{arquivo.stem}", sem_municipio)
    declaracoes = declaracoes.dropna(subset=["municipio_id"]).copy()
    declaracoes["vigente"] = False  # recalculado no banco, considerando todas as edições já carregadas
    ids_validos = set(declaracoes["id"])

    fonte_id = registrar_fonte(conn, config.FONTE_MUNICIPAL, None, None)
    declaracoes["fonte_id"] = fonte_id

    upsert(conn, "tipo_residuo", r.tipos_residuo, ["descricao"], ["descricao"])
    tipos = _mapa_ids(conn, "tipo_residuo")
    materiais = r.materiais.assign(tipo_residuo_id=r.materiais["tipo_residuo_descricao"].map(tipos))
    upsert(conn, "material", materiais, ["descricao", "tipo_residuo_id"], ["descricao"])
    upsert(conn, "destinacao", r.destinacoes, ["descricao", "categoria"], ["descricao"],
           atualizar={"categoria": "excluded.categoria"})
    mats = _mapa_ids(conn, "material")
    dests = _mapa_ids(conn, "destinacao")

    colunas_decl = ["id", "municipio_id", "fonte_id", "declarante", "ano", "ano_referencia",
                    "data_criacao", "data_entrega", "possui_coleta_seletiva", "possui_plano_gestao",
                    "link_plano", "periodicidade_revisao_texto", "periodicidade_revisao_anos",
                    "ano_ultima_versao_plano", "vigente"]
    n_decl = upsert(conn, "declaracao", declaracoes.astype({"municipio_id": "int64"}), colunas_decl, ["id"],
                    atualizar={c: f"excluded.{c}" for c in colunas_decl if c != "id"})

    geracoes = r.geracoes[r.geracoes["declaracao_id"].isin(ids_validos)].assign(
        tipo_residuo_id=lambda d: d["tipo_residuo"].map(tipos)
    )
    upsert(conn, "geracao_residuo", geracoes, ["declaracao_id", "tipo_residuo_id", "massa_ton"],
           ["declaracao_id", "tipo_residuo_id"], atualizar={"massa_ton": "excluded.massa_ton"})
    ger_ids = ler_tabela(conn, "select id as geracao_id, declaracao_id, tipo_residuo_id from public.geracao_residuo")

    composicoes = (
        r.composicoes[r.composicoes["declaracao_id"].isin(ids_validos)]
        .assign(tipo_residuo_id=lambda d: d["tipo_residuo"].map(tipos),
                material_id=lambda d: d["material"].map(mats))
        .merge(ger_ids, on=["declaracao_id", "tipo_residuo_id"])
    )
    upsert(conn, "composicao_material", composicoes, ["geracao_id", "material_id", "percentual"],
           ["geracao_id", "material_id"], atualizar={"percentual": "excluded.percentual"})
    comp_ids = ler_tabela(conn, "select id as composicao_id, geracao_id, material_id from public.composicao_material")

    dest_mat = (
        r.destinacoes_material[r.destinacoes_material["declaracao_id"].isin(ids_validos)]
        .assign(tipo_residuo_id=lambda d: d["tipo_residuo"].map(tipos),
                material_id=lambda d: d["material"].map(mats),
                destinacao_id=lambda d: d["destinacao"].map(dests))
        .merge(ger_ids, on=["declaracao_id", "tipo_residuo_id"])
        .merge(comp_ids, on=["geracao_id", "material_id"])
    )
    upsert(conn, "destinacao_material", dest_mat, ["composicao_id", "destinacao_id", "percentual"],
           ["composicao_id", "destinacao_id"], atualizar={"percentual": "excluded.percentual"})

    metas = r.metas[r.metas["declaracao_id"].isin(ids_validos)]
    with conn.cursor() as cur:
        cur.execute("delete from public.meta where declaracao_id = any(%s)", (sorted(int(i) for i in ids_validos),))
    n_metas = upsert(conn, "meta", metas,
                     ["declaracao_id", "tipo", "valor_atual", "valor_meta", "prazo_texto", "prazo_ano",
                      "programa", "programa_descritivo"], ["id"])

    return ResumoCarga(f"municipal ({arquivo.name})", {
        "declaracoes": n_decl,
        "declaracoes_sem_municipio": len(sem_municipio),
        "geracoes": len(geracoes),
        "composicoes": len(composicoes),
        "destinacoes_material": len(dest_mat),
        "metas": n_metas,
    })


def recalcular_declaracoes_vigentes(conn: Conexao) -> int:
    """Por município, vale a declaração com a data de entrega mais recente (desempate pelo maior id),
    entre todas as edições carregadas (2022, 2024, 2025...)."""
    with conn.cursor() as cur:
        cur.execute("update public.declaracao set vigente = false where vigente")
        cur.execute(
            """
            update public.declaracao d set vigente = true
            from (
              select distinct on (municipio_id) id
              from public.declaracao
              order by municipio_id, data_entrega desc, id desc
            ) ultima
            where d.id = ultima.id
            """
        )
        return cur.rowcount


def carregar_municipais(conn: Conexao, arquivos: list[Path], relatorios_dir: Path) -> list[ResumoCarga]:
    resumos = [carregar_municipal(conn, arquivo, relatorios_dir) for arquivo in arquivos]
    vigentes = recalcular_declaracoes_vigentes(conn)
    resumos.append(ResumoCarga("municipal_vigentes", {"municipios_com_declaracao_vigente": vigentes}))
    return resumos


def atualizar_views(conn: Conexao) -> None:
    with conn.cursor() as cur:
        cur.execute("select public.atualizar_views()")
