import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { cliente, executar } from '@/api/cliente';
import { useDebounce } from '@/hooks/useDebounce';

/** Termo válido para a API (2 a 80 caracteres) ou `null` para "sem termo". */
function termo(texto: string): string | null {
  const t = texto.trim();
  return t.length >= 2 ? t.slice(0, 80) : null;
}

/** Sem termo, a API devolve os resíduos com mais oportunidades. */
export function useBuscaResiduos(texto: string, perigoso: boolean | null) {
  const q = termo(useDebounce(texto));
  return useQuery({
    queryKey: ['residuos', q, perigoso],
    placeholderData: keepPreviousData,
    queryFn: ({ signal }) =>
      executar(
        (s) =>
          cliente.GET('/v1/residuos', {
            params: { query: { q, perigoso, limite: 20 } },
            signal: s,
          }),
        signal,
      ),
  });
}

export function useBuscaMunicipios(texto: string, uf: string | null) {
  const q = termo(useDebounce(texto));
  return useQuery({
    queryKey: ['municipios', uf, q],
    enabled: q !== null,
    placeholderData: keepPreviousData,
    queryFn: ({ signal }) =>
      executar(
        (s) =>
          cliente.GET('/v1/municipios', {
            params: { query: { q, uf, limite: 20 } },
            signal: s,
          }),
        signal,
      ),
  });
}
