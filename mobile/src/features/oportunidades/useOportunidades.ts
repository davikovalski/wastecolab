import { useInfiniteQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import { cliente, executar } from '@/api/cliente';
import type { OportunidadeItem, PaginaOportunidades } from '@/api/tipos';
import { type Filtros, paraConsulta } from '@/features/filtros/filtros';
import { POR_PAGINA } from '@/lib/constantes';

export const chaveOportunidades = (f: Filtros) => ['oportunidades', paraConsulta(f)] as const;

export function proximaPagina(ultima: PaginaOportunidades): number | undefined {
  return ultima.pagina * ultima.por_pagina < ultima.total ? ultima.pagina + 1 : undefined;
}

/** Lista paginada (HU1). O mapa (HU2) usa a mesma consulta: trocar de tela não busca de novo. */
export function useOportunidades(filtros: Filtros) {
  const consulta = useInfiniteQuery({
    queryKey: chaveOportunidades(filtros),
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) =>
      executar(
        (s) =>
          cliente.GET('/v1/oportunidades', {
            params: { query: { ...paraConsulta(filtros), pagina: pageParam, por_pagina: POR_PAGINA } },
            signal: s,
          }),
        signal,
      ),
    getNextPageParam: proximaPagina,
  });

  const itens = useMemo<OportunidadeItem[]>(() => consulta.data?.pages.flatMap((p) => p.itens) ?? [], [consulta.data]);
  const total = consulta.data?.pages[0]?.total ?? 0;

  return { ...consulta, itens, total };
}
