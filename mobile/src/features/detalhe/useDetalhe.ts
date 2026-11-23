import { useQuery } from '@tanstack/react-query';

import { cliente, executar } from '@/api/cliente';
import type { RaioKm } from '@/lib/constantes';

export interface ChaveDetalhe {
  cnpj: string;
  codigo: string;
  raioKm: RaioKm;
}

/** Detalhe com destinadores (HU3). O mapa usa o mesmo hook, então o detalhe já abre do cache. */
export function useDetalhe(chave: ChaveDetalhe | null) {
  return useQuery({
    queryKey: ['detalhe', chave?.cnpj, chave?.codigo, chave?.raioKm],
    enabled: chave !== null,
    queryFn: ({ signal }) => {
      if (chave === null) throw new Error('consulta desabilitada');
      return executar(
        (s) =>
          cliente.GET('/v1/oportunidades/{cnpj}/{codigo_residuo}', {
            params: { path: { cnpj: chave.cnpj, codigo_residuo: chave.codigo }, query: { raio_km: chave.raioKm } },
            signal: s,
          }),
        signal,
      );
    },
  });
}
