import { erroApi, json, pagina, semRede, simularApi } from '@/test/api';

import { cliente, executar } from './cliente';
import { deveRepetir, ErroApi, ErroRede, mensagemDoErro } from './erros';

const listar = (sinal?: AbortSignal, timeoutMs?: number) =>
  executar(
    (s) => cliente.GET('/v1/oportunidades', { params: { query: { raio_km: 100 } }, signal: s }),
    sinal,
    timeoutMs,
  );

describe('cliente da API', () => {
  it('devolve os dados tipados e envia os parâmetros', async () => {
    const fetch = simularApi(() => json(pagina([])));
    await expect(listar()).resolves.toEqual(pagina([]));
    const requisicao = fetch.mock.calls[0]?.[0] as Request;
    expect(new URL(requisicao.url).searchParams.get('raio_km')).toBe('100');
  });

  it('converte o formato único de erro em ErroApi', async () => {
    simularApi(() => erroApi(404, 'nao_encontrado'));
    const erro = await listar().catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro).toMatchObject({ status: 404, codigo: 'nao_encontrado' });
  });

  it('trata corpo de erro inesperado pelo status', async () => {
    simularApi(() => new Response('Bad gateway', { status: 503 }));
    await expect(listar()).rejects.toMatchObject({ codigo: 'banco_indisponivel' });
  });

  it('falha de conexão vira ErroRede sem_conexao', async () => {
    semRede();
    const erro = await listar().catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroRede);
    expect(erro).toMatchObject({ codigo: 'sem_conexao' });
  });

  it('estoura o timeout', async () => {
    globalThis.fetch = jest.fn(
      (req: Request) =>
        new Promise<Response>((_, rejeitar) => {
          req.signal.addEventListener('abort', () => rejeitar(new DOMException('Aborted', 'AbortError')));
        }),
    ) as unknown as typeof fetch;
    await expect(listar(undefined, 20)).rejects.toMatchObject({ codigo: 'timeout' });
  });

  it('cancelamento pelo TanStack Query não vira erro de rede', async () => {
    globalThis.fetch = jest.fn(
      (req: Request) =>
        new Promise<Response>((_, rejeitar) => {
          req.signal.addEventListener('abort', () => rejeitar(new DOMException('Aborted', 'AbortError')));
        }),
    ) as unknown as typeof fetch;
    const controle = new AbortController();
    const promessa = listar(controle.signal);
    controle.abort();
    const erro = await promessa.catch((e: unknown) => e);
    expect(erro).not.toBeInstanceOf(ErroRede);
  });
});

describe('deveRepetir', () => {
  it('repete só em rede e banco indisponível', () => {
    expect(deveRepetir(new ErroRede('sem_conexao'))).toBe(true);
    expect(deveRepetir(new ErroRede('timeout'))).toBe(true);
    expect(deveRepetir(new ErroApi(503, 'banco_indisponivel', ''))).toBe(true);
    expect(deveRepetir(new ErroApi(404, 'nao_encontrado', ''))).toBe(false);
    expect(deveRepetir(new ErroApi(422, 'parametro_invalido', ''))).toBe(false);
    expect(deveRepetir(new Error('x'))).toBe(false);
  });

  it('tem mensagem para cada código', () => {
    expect(mensagemDoErro(new ErroRede('sem_conexao'))).toMatch(/conexão/);
    expect(mensagemDoErro(new Error('x'))).toBe('Algo deu errado.');
  });
});
