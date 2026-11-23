/**
 * Cliente HTTP tipado pelo contrato OpenAPI da API (schema.d.ts, gerado por `npm run gerar:api`).
 * Toda chamada passa por `executar`, que aplica o timeout e converte falhas em ErroApi/ErroRede.
 */
import createClient from 'openapi-fetch';

import { API_URL, TIMEOUT_MS } from '@/lib/constantes';

import { ErroApi, ErroRede, erroDaResposta } from './erros';
import type { paths } from './schema';

// O wrapper lê `globalThis.fetch` a cada chamada (permite simular a API nos testes).
export const cliente = createClient<paths>({
  baseUrl: API_URL,
  fetch: (requisicao: Request) => globalThis.fetch(requisicao),
});

interface Resposta<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/**
 * Executa uma chamada com timeout. `sinal` é o AbortSignal do TanStack Query: se a consulta for
 * cancelada, o erro de cancelamento sobe como está (o Query o ignora).
 */
export async function executar<T>(
  chamada: (sinal: AbortSignal) => Promise<Resposta<T>>,
  sinal?: AbortSignal,
  timeoutMs: number = TIMEOUT_MS,
): Promise<T> {
  const controle = new AbortController();
  let estourou = false;
  const timer = setTimeout(() => {
    estourou = true;
    controle.abort();
  }, timeoutMs);
  const cancelar = () => controle.abort();
  sinal?.addEventListener('abort', cancelar);
  try {
    const { data, error, response } = await chamada(controle.signal);
    if (!response.ok) throw erroDaResposta(response.status, error);
    if (data === undefined) throw new ErroApi(response.status, 'erro_interno', 'Resposta vazia');
    return data;
  } catch (erro) {
    if (erro instanceof ErroApi) throw erro;
    if (estourou) throw new ErroRede('timeout');
    if (sinal?.aborted) throw erro;
    throw new ErroRede('sem_conexao');
  } finally {
    clearTimeout(timer);
    sinal?.removeEventListener('abort', cancelar);
  }
}
