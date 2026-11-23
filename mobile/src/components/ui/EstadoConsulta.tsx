import type { ReactNode } from 'react';

import { ErroRede } from '@/api/erros';

import { ErrorState } from './ErrorState';

interface ConsultaBasica {
  isPending: boolean;
  isError: boolean;
  fetchStatus: 'fetching' | 'paused' | 'idle';
  error: unknown;
  data: unknown;
  isRefetching: boolean;
  refetch: () => unknown;
}

interface Props {
  consulta: ConsultaBasica;
  carregando: ReactNode;
  children: ReactNode;
}

/**
 * Loading → erro → conteúdo, igual em todas as telas.
 * Offline e sem nada no cache, a consulta fica "pausada": mostramos o erro de conexão em vez de um
 * skeleton infinito. Com cache, o conteúdo aparece normalmente (e o banner offline avisa).
 */
export function EstadoConsulta({ consulta, carregando, children }: Props) {
  if (consulta.isPending && consulta.fetchStatus === 'paused') {
    return (
      <ErrorState
        erro={new ErroRede('sem_conexao')}
        mensagem="Você está offline e ainda não há dados salvos para esta busca."
        onTentarNovamente={() => void consulta.refetch()}
      />
    );
  }
  if (consulta.isPending) return <>{carregando}</>;
  // Erro numa atualização com dados já em tela: mantém os dados (o pull-to-refresh tenta de novo).
  if (consulta.isError && consulta.data === undefined) {
    return (
      <ErrorState
        erro={consulta.error}
        tentando={consulta.isRefetching}
        onTentarNovamente={() => void consulta.refetch()}
      />
    );
  }
  return <>{children}</>;
}
