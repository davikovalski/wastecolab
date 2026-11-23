"""Carga no PostgreSQL: COPY para uma tabela temporária + INSERT ... ON CONFLICT."""

import math
from collections.abc import Iterator, Sequence
from datetime import date

import pandas as pd
from psycopg import Connection, sql

ValorSql = str | int | float | bool | date | None


def _python(valor: object) -> ValorSql:
    """Converte valores do pandas/numpy para tipos aceitos pelo psycopg."""
    if valor is None or valor is pd.NA or valor is pd.NaT:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, bool | str | int | float | date):
        return valor
    item = getattr(valor, "item", None)  # escalares numpy
    if callable(item):
        convertido = item()
        if isinstance(convertido, bool | str | int | float | date):
            return convertido
    raise TypeError(f"Valor sem conversão para SQL: {valor!r} ({type(valor).__name__})")


def _linhas(df: pd.DataFrame, colunas: Sequence[str]) -> Iterator[tuple[ValorSql, ...]]:
    for linha in df[list(colunas)].itertuples(index=False, name=None):
        yield tuple(_python(v) for v in linha)


def copiar_para_temporaria(
    conn: Connection[tuple[object, ...]],
    tabela_destino: str,
    df: pd.DataFrame,
    colunas: Sequence[str],
    tipos_extras: dict[str, str] | None = None,
) -> str:
    """Cria `_stg_<tabela>` com as colunas (e tipos) da tabela de destino e copia o DataFrame."""
    temporaria = f"_stg_{tabela_destino}"
    extras = tipos_extras or {}
    colunas_tabela = [c for c in colunas if c not in extras]
    with conn.cursor() as cur:
        cur.execute(sql.SQL("drop table if exists {}").format(sql.Identifier(temporaria)))
        cur.execute(
            sql.SQL("create temp table {} as select {} from public.{} with no data").format(
                sql.Identifier(temporaria),
                sql.SQL(", ").join(sql.Identifier(c) for c in colunas_tabela) if colunas_tabela
                else sql.SQL("1 as _vazio"),
                sql.Identifier(tabela_destino),
            )
        )
        for coluna, tipo in extras.items():
            cur.execute(
                sql.SQL("alter table {} add column {} " + tipo).format(
                    sql.Identifier(temporaria), sql.Identifier(coluna)
                )
            )
        copia = sql.SQL("copy {} ({}) from stdin").format(
            sql.Identifier(temporaria), sql.SQL(", ").join(sql.Identifier(c) for c in colunas)
        )
        with cur.copy(copia) as copy:
            for linha in _linhas(df, colunas):
                copy.write_row(linha)
    return temporaria


def upsert(
    conn: Connection[tuple[object, ...]],
    tabela: str,
    df: pd.DataFrame,
    colunas: Sequence[str],
    chave: Sequence[str],
    atualizar: dict[str, str] | None = None,
) -> int:
    """Insere ou atualiza linhas. `atualizar` mapeia coluna -> expressão SQL do SET
    (use `excluded.col` e `t.col`). Sem `atualizar`, conflitos são ignorados."""
    if df.empty:
        return 0
    temporaria = copiar_para_temporaria(conn, tabela, df, colunas)
    lista = sql.SQL(", ").join(sql.Identifier(c) for c in colunas)
    acao: sql.Composable
    if atualizar:
        acao = sql.SQL("do update set ") + sql.SQL(", ").join(
            sql.SQL("{} = " + expressao).format(sql.Identifier(coluna))
            for coluna, expressao in atualizar.items()
        )
    else:
        acao = sql.SQL("do nothing")
    comando = sql.SQL(
        "insert into public.{tabela} as t ({lista}) select {lista} from {tmp} on conflict ({chave}) {acao}"
    ).format(
        tabela=sql.Identifier(tabela),
        lista=lista,
        tmp=sql.Identifier(temporaria),
        chave=sql.SQL(", ").join(sql.Identifier(c) for c in chave),
        acao=acao,
    )
    with conn.cursor() as cur:
        cur.execute(comando)
        return cur.rowcount


def registrar_fonte(
    conn: Connection[tuple[object, ...]], nome: str, url: str | None, atualizado_na_fonte: date | None
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.fonte_dado (nome, url, atualizado_na_fonte)
            values (%s, %s, %s)
            on conflict (nome) do update
              set url = excluded.url,
                  atualizado_na_fonte = excluded.atualizado_na_fonte,
                  importado_em = now()
            returning id
            """,
            (nome, url, atualizado_na_fonte),
        )
        linha = cur.fetchone()
    if linha is None or not isinstance(linha[0], int):
        raise RuntimeError("Não foi possível registrar a fonte de dados.")
    return linha[0]


def ler_tabela(conn: Connection[tuple[object, ...]], consulta: str) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(consulta)
        nomes = [d.name for d in cur.description or []]
        return pd.DataFrame(cur.fetchall(), columns=nomes)
