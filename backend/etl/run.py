"""Ponto de entrada do ETL.

Exemplos:
    python -m etl.run todas --municipal "data/Municipal - Diagnostico.csv"
    python -m etl.run ibge
    python -m etl.run ibama --sem-gerador     # pula o arquivo de 830 MB
    python -m etl.run municipal --municipal data/diagnostico.csv
"""

import argparse
import logging
import sys
from pathlib import Path

import psycopg

from etl import config, pipelines
from etl.extractors import fontes

log = logging.getLogger("etl")


def _argumentos(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m etl.run", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("etapa", choices=["ibge", "ibama", "municipal", "todas"])
    parser.add_argument("--municipal", type=Path, help="CSV do diagnóstico municipal")
    parser.add_argument("--destinador", type=Path, help="CSV local do IBAMA (destinador)")
    parser.add_argument("--gerador", type=Path, help="CSV local do IBAMA (gerador)")
    parser.add_argument("--ibge", type=Path, help="CSV local de municípios do IBGE")
    parser.add_argument("--sem-gerador", action="store_true",
                        help="Não lê o arquivo do gerador (os geradores ficam sem município)")
    parser.add_argument("--baixar-novamente", action="store_true", help="Ignora arquivos já baixados")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _argumentos(sys.argv[1:] if argv is None else argv)
    ajustes = config.Settings()  # type: ignore[call-arg]  # database_url vem do ambiente
    dados = ajustes.dados_dir
    etapas = ["ibge", "ibama", "municipal"] if args.etapa == "todas" else [args.etapa]
    if "municipal" in etapas and args.municipal is None:
        log.error("Informe --municipal com o caminho do CSV do diagnóstico municipal.")
        return 2

    with psycopg.connect(ajustes.database_url) as conn:
        for etapa in etapas:
            if etapa == "ibge":
                arquivo = args.ibge or fontes.baixar(
                    config.URL_MUNICIPIOS_IBGE, dados / "municipios_ibge.csv", args.baixar_novamente
                ).caminho
                resumo = pipelines.carregar_ibge(conn, arquivo)
            elif etapa == "ibama":
                if args.destinador is not None:
                    destinador = fontes.ArquivoBaixado(args.destinador, None)
                else:
                    destinador = fontes.baixar(config.URL_IBAMA_DESTINADOR,
                                               dados / "ibama_destinador.csv", args.baixar_novamente)
                gerador: Path | None = None
                if not args.sem_gerador:
                    gerador = args.gerador or fontes.baixar(
                        config.URL_IBAMA_GERADOR, dados / "ibama_gerador.csv", args.baixar_novamente
                    ).caminho
                resumo = pipelines.carregar_ibama(
                    conn, destinador.caminho, gerador, destinador.atualizado_na_fonte,
                    ajustes.relatorios_dir, ajustes.tamanho_lote_gerador,
                )
            else:
                resumo = pipelines.carregar_municipal(conn, args.municipal, ajustes.relatorios_dir)
            conn.commit()
            log.info("Concluído %s", resumo)
        pipelines.atualizar_views(conn)
        conn.commit()
        log.info("Views materializadas atualizadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
