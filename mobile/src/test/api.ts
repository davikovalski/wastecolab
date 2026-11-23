/** Simula a API trocando o `fetch` global (o cliente lê `globalThis.fetch` a cada chamada). */
import type { DetalheOportunidade, OportunidadeItem, PaginaOportunidades } from '@/api/tipos';

export type Rota = (url: URL) => Response | Promise<Response>;

export function json(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } });
}

export function erroApi(status: number, codigo: string): Response {
  return json({ erro: { codigo, mensagem: codigo, detalhes: null } }, status);
}

export function simularApi(rota: Rota): jest.Mock {
  const mock = jest.fn(async (entrada: Request | string) => {
    const url = new URL(typeof entrada === 'string' ? entrada : entrada.url);
    return rota(url);
  });
  globalThis.fetch = mock as unknown as typeof fetch;
  return mock;
}

export function semRede(): jest.Mock {
  const mock = jest.fn(async () => {
    throw new TypeError('Network request failed');
  });
  globalThis.fetch = mock as unknown as typeof fetch;
  return mock;
}

export function item(n: number, extra: Partial<OportunidadeItem> = {}): OportunidadeItem {
  return {
    gerador: {
      cnpj: String(11111111000100 + n).padStart(14, '0'),
      razao_social: `Indústria ${n} Ltda`,
      municipio: { id_ibge: 3550308, nome: 'São Paulo', uf: 'SP' },
    },
    residuo: { codigo: '070213', descricao: 'Resíduos de plásticos', perigoso: false },
    ano: 2024,
    operacoes_atuais: [{ codigo: 'D5', descricao: 'Aterramentos especialmente projetados' }],
    quantidade: { toneladas: 15.001, litros: null, unidades: null },
    rotas: { total: 2, distancia_mais_proxima_km: 12.4 },
    localizacao: { lat: -23.55, lon: -46.63, precisao: 'municipio' },
    ...extra,
  };
}

export function pagina(itens: OportunidadeItem[], total = itens.length, numero = 1): PaginaOportunidades {
  return { itens, pagina: numero, por_pagina: 20, total, raio_km: 100 };
}

export function detalhe(rotas = 1): DetalheOportunidade {
  const base = item(1);
  return {
    oportunidade: {
      gerador: { ...base.gerador, categoria_atividade: 'Indústria Química', detalhe_atividade: null },
      residuo: base.residuo,
      ano: base.ano,
      operacoes_atuais: base.operacoes_atuais,
      quantidade: base.quantidade,
      localizacao: base.localizacao,
    },
    raio_km: 100,
    rotas: Array.from({ length: rotas }, (_, i) => ({
      destinador: {
        cnpj: String(22222222000100 + i).padStart(14, '0'),
        razao_social: `Recicladora ${i}`,
        municipio: { id_ibge: 3530805, nome: 'Mogi Mirim', uf: 'SP' },
      },
      distancia_km: 40 + i,
      operacoes: [{ codigo: 'R3', descricao: 'Reciclagem de substâncias orgânicas' }],
      ano_mais_recente: 2024,
      quantidade_recebida: { toneladas: 120, litros: null, unidades: null },
      localizacao: { lat: -22.43, lon: -46.95, precisao: 'municipio' },
      contexto_municipal:
        i === 0
          ? null
          : {
              ano_referencia: 2024,
              possui_coleta_seletiva: true,
              possui_plano_gestao: true,
              link_plano: 'https://exemplo.gov.br/plano.pdf',
              ano_ultima_versao_plano: 2020,
              metas: [
                {
                  tipo: 'reciclagem',
                  valor_atual: 10,
                  valor_meta: 30,
                  prazo_texto: null,
                  prazo_ano: 2030,
                  programa: null,
                },
              ],
            },
    })),
    fontes: [
      {
        nome: 'IBAMA RAPP - Resíduos Sólidos',
        url: null,
        atualizado_na_fonte: '2026-03-01',
        importado_em: '2026-11-23T09:40:00Z',
      },
    ],
  };
}
