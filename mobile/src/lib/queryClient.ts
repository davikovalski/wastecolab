import AsyncStorage from '@react-native-async-storage/async-storage';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { QueryClient } from '@tanstack/react-query';

import { deveRepetir } from '@/api/erros';

import { CACHE_OFFLINE_MS, DADOS_FRESCOS_MS } from './constantes';

export function criarQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: DADOS_FRESCOS_MS,
        gcTime: CACHE_OFFLINE_MS,
        // Até 2 novas tentativas, e só quando o erro pode ser passageiro (rede ou banco fora do ar).
        retry: (falhas, erro) => falhas < 2 && deveRepetir(erro),
      },
    },
  });
}

export const persister = createAsyncStoragePersister({
  storage: AsyncStorage,
  key: 'wastecolab-cache-v1',
});

export const OPCOES_PERSISTENCIA = {
  persister,
  maxAge: CACHE_OFFLINE_MS,
  // Troque quando o formato das respostas mudar, para descartar o cache antigo.
  buster: 'api-v1',
} as const;
