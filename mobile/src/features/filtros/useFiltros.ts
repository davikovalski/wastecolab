import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useMemo } from 'react';

import { type Filtros, FILTROS_PADRAO, lerFiltros, type ParamsUrl, paraParams } from './filtros';

export type Visao = 'lista' | 'mapa';

const ROTA: Record<Visao, '/' | '/mapa'> = { lista: '/', mapa: '/mapa' };

/** Filtros da tela atual, lidos e gravados nos search params. */
export function useFiltros() {
  const params = useLocalSearchParams<ParamsUrl>();
  const chave = JSON.stringify(params);
  // `params` muda de identidade a cada render; a chave em texto mantém os filtros estáveis.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const filtros = useMemo(() => lerFiltros(params), [chave]);

  const aplicar = useCallback((novos: Filtros) => router.setParams(paraParams(novos)), []);
  const limpar = useCallback(() => router.setParams(paraParams(FILTROS_PADRAO)), []);
  /** Troca entre lista e mapa levando os mesmos filtros. */
  const irPara = useCallback(
    (visao: Visao) => router.replace({ pathname: ROTA[visao], params: definidos(paraParams(filtros)) }),
    [filtros],
  );

  return { filtros, aplicar, limpar, irPara };
}

function definidos(p: Record<string, string | undefined>): Record<string, string> {
  return Object.fromEntries(Object.entries(p).filter((e): e is [string, string] => e[1] !== undefined));
}
