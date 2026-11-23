/**
 * Estados de loading, vazio, erro e offline de cada tela, com o roteador real e a API simulada.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { onlineManager } from '@tanstack/react-query';
import { act, fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import path from 'node:path';

import { detalhe, erroApi, item, json, pagina, semRede, simularApi } from '@/test/api';

const APP = path.resolve(__dirname, '../app');

// A persistência real grava no AsyncStorage com atraso e vazaria dados de um teste para o outro.
jest.mock('@/lib/queryClient', () => {
  const real = jest.requireActual<typeof import('@/lib/queryClient')>('@/lib/queryClient');
  const persister = {
    persistClient: async () => undefined,
    restoreClient: async () => undefined,
    removeClient: async () => undefined,
  };
  return { ...real, OPCOES_PERSISTENCIA: { ...real.OPCOES_PERSISTENCIA, persister } };
});

beforeEach(async () => {
  await AsyncStorage.clear();
  onlineManager.setOnline(true);
});

/** Toque que dispara navegação ou busca: espera o act assíncrono terminar. */
async function tocar(elemento: Parameters<typeof fireEvent.press>[0]): Promise<void> {
  await act(async () => fireEvent.press(elemento));
}

function pendente(): Promise<Response> {
  return new Promise(() => undefined);
}

describe('Lista (HU1)', () => {
  it('mostra skeleton enquanto carrega', async () => {
    simularApi(pendente);
    await renderRouter(APP, { initialUrl: '/' });
    expect(screen.getByTestId('skeleton-lista')).toBeOnTheScreen();
  });

  it('mostra os itens com quantidade, operação e rotas', async () => {
    simularApi(() => json(pagina([item(1), item(2)], 2)));
    await renderRouter(APP, { initialUrl: '/' });
    expect(await screen.findByText('Indústria 1 Ltda')).toBeOnTheScreen();
    expect(screen.getByText('2 oportunidades')).toBeOnTheScreen();
    expect(screen.getAllByText('15 t')).toHaveLength(2);
    expect(screen.getAllByText(/D5 – Aterramentos/)).toHaveLength(2);
    expect(screen.getAllByText('2 destinadores valorizadores em até 100 km')).toHaveLength(2);
    expect(screen.getAllByText('Mais próximo a 12 km')).toHaveLength(2);
  });

  it('vazio oferece aumentar raio e limpar filtros', async () => {
    const fetch = simularApi(() => json(pagina([])));
    const router = await renderRouter(APP, { initialUrl: '/?uf=SP' });
    expect(await screen.findByText('Nenhuma oportunidade')).toBeOnTheScreen();
    expect(screen.getByText('Limpar filtros')).toBeOnTheScreen();

    await tocar(screen.getByText('Aumentar raio para 250 km'));
    await waitFor(() => expect(router.getSearchParams()).toMatchObject({ raio: '250', uf: 'SP' }));
    await waitFor(() => {
      const ultima = fetch.mock.calls.at(-1)?.[0] as Request;
      expect(new URL(ultima.url).searchParams.get('raio_km')).toBe('250');
    });
    expect(await screen.findByText('Aumentar raio para 500 km')).toBeOnTheScreen();
  });

  it('erro da API mostra mensagem e Tentar novamente', async () => {
    let falhar = true;
    simularApi(() => (falhar ? erroApi(500, 'erro_interno') : json(pagina([item(1)]))));
    await renderRouter(APP, { initialUrl: '/' });
    expect(await screen.findByText('Algo deu errado no servidor.')).toBeOnTheScreen();
    falhar = false;
    await tocar(screen.getByText('Tentar novamente'));
    expect(await screen.findByText('Indústria 1 Ltda')).toBeOnTheScreen();
  });

  it('offline sem cache explica que não há dados salvos', async () => {
    semRede();
    onlineManager.setOnline(false);
    await renderRouter(APP, { initialUrl: '/' });
    expect(await screen.findByText('Você está offline e ainda não há dados salvos para esta busca.')).toBeOnTheScreen();
    expect(screen.getByText('Você está offline')).toBeOnTheScreen();
  });

  it('offline mantém o último resultado na tela, com a data', async () => {
    simularApi(() => json(pagina([item(1)])));
    await renderRouter(APP, { initialUrl: '/' });
    await screen.findByText('Indústria 1 Ltda');
    semRede();
    await act(async () => onlineManager.setOnline(false));
    expect(await screen.findByText('Você está offline')).toBeOnTheScreen();
    expect(screen.getByText('Indústria 1 Ltda')).toBeOnTheScreen();
    expect(screen.getByText(/^Dados de \d{2}\/\d{2}, \d{2}:\d{2}$/)).toBeOnTheScreen();
  });

  it('carrega a próxima página ao chegar no fim', async () => {
    const fetch = simularApi((url) =>
      url.searchParams.get('pagina') === '2'
        ? json(pagina([item(21)], 21, 2))
        : json(
            pagina(
              Array.from({ length: 20 }, (_, i) => item(i + 1)),
              21,
            ),
          ),
    );
    await renderRouter(APP, { initialUrl: '/' });
    expect(await screen.findByText('21 oportunidades')).toBeOnTheScreen();
    await act(async () => fireEvent(screen.getByTestId('lista-oportunidades'), 'onEndReached'));
    await waitFor(() =>
      expect(fetch.mock.calls.some(([r]) => new URL((r as Request).url).searchParams.get('pagina') === '2')).toBe(true),
    );
  });
});

describe('Mapa (HU2)', () => {
  it('usa os mesmos filtros e a mesma consulta da lista', async () => {
    const fetch = simularApi(() => json(pagina([item(1)])));
    const router = await renderRouter(APP, { initialUrl: '/?uf=SP&raio=250' });
    await screen.findByText('Indústria 1 Ltda');
    await tocar(screen.getByText('Mapa'));
    await waitFor(() => expect(router.getPathname()).toBe('/mapa'));
    expect(router.getSearchParams()).toMatchObject({ uf: 'SP', raio: '250' });
    expect(await screen.findByText('Localização aproximada (centro do município)')).toBeOnTheScreen();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('tocar no município mostra o cartão e as linhas até os destinadores', async () => {
    simularApi((url) => (url.pathname.endsWith('/070213') ? json(detalhe(2)) : json(pagina([item(1)]))));
    await renderRouter(APP, { initialUrl: '/mapa' });
    await screen.findByText('Localização aproximada (centro do município)');
    // No zoom inicial (Brasil) há um único município: aparece como marcador próprio.
    await act(async () => fireEvent(screen.getAllByTestId('marcador')[0]!, 'touchEnd'));
    expect(await screen.findByTestId('cartao-municipio')).toBeOnTheScreen();
    expect(screen.getByText('Ver detalhe')).toBeOnTheScreen();
    await waitFor(() => expect(screen.getAllByTestId('linha')).toHaveLength(2));
  });

  it('vazio segue a regra da lista', async () => {
    simularApi(() => json(pagina([])));
    await renderRouter(APP, { initialUrl: '/mapa' });
    expect(await screen.findByText('Nenhuma oportunidade')).toBeOnTheScreen();
  });

  it('offline avisa e oferece voltar para a lista', async () => {
    simularApi(() => json(pagina([item(1)])));
    const router = await renderRouter(APP, { initialUrl: '/mapa' });
    await screen.findByText('Localização aproximada (centro do município)');
    await act(async () => onlineManager.setOnline(false));
    await tocar(await screen.findByText('Ver em lista'));
    await waitFor(() => expect(router.getPathname()).toBe('/'));
  });
});

describe('Detalhe (HU3)', () => {
  const url = '/oportunidade/11111111000101/070213?raio=100';

  it('mostra skeleton enquanto carrega', async () => {
    simularApi(pendente);
    await renderRouter(APP, { initialUrl: url });
    expect(screen.getByTestId('skeleton-detalhe')).toBeOnTheScreen();
  });

  it('mostra gerador, rotas, contexto municipal e fontes', async () => {
    simularApi(() => json(detalhe(2)));
    await renderRouter(APP, { initialUrl: url });
    expect(await screen.findByText('Indústria 1 Ltda')).toBeOnTheScreen();
    expect(screen.getByText(/11\.111\.111\/0001-01/)).toBeOnTheScreen();
    expect(screen.getByText('2 destinadores em até 100 km')).toBeOnTheScreen();
    expect(screen.getByText('Recicladora 0')).toBeOnTheScreen();
    expect(screen.getByText('Município sem diagnóstico')).toBeOnTheScreen();
    expect(screen.getByText(/Reciclagem: hoje 10%, meta 30% até 2030/)).toBeOnTheScreen();
    expect(screen.getByText(/IBAMA RAPP - Resíduos Sólidos · atualizado na fonte: 01\/03\/2026/)).toBeOnTheScreen();
  });

  it('sem destinador no raio oferece aumentar o raio', async () => {
    const fetch = simularApi(() => json(detalhe(0)));
    await renderRouter(APP, { initialUrl: url });
    expect(await screen.findByText('Nenhum destinador no raio')).toBeOnTheScreen();
    await tocar(screen.getByText('Aumentar raio para 250 km'));
    await waitFor(() => {
      const ultima = fetch.mock.calls.at(-1)?.[0] as Request;
      expect(new URL(ultima.url).searchParams.get('raio_km')).toBe('250');
    });
  });

  it('404 mostra mensagem e Tentar novamente', async () => {
    simularApi(() => erroApi(404, 'nao_encontrado'));
    await renderRouter(APP, { initialUrl: url });
    expect(await screen.findByText(/Não encontramos esta oportunidade/)).toBeOnTheScreen();
    expect(screen.getByText('Tentar novamente')).toBeOnTheScreen();
  });

  it('link inválido não chama a API', async () => {
    const fetch = simularApi(() => json(detalhe()));
    await renderRouter(APP, { initialUrl: '/oportunidade/123/070213' });
    expect(await screen.findByText('Link inválido')).toBeOnTheScreen();
    expect(fetch).not.toHaveBeenCalled();
  });
});
