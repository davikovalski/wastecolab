import { item } from '@/test/api';

import {
  agruparPorMunicipio,
  bboxDaRegiao,
  criarIndice,
  REGIAO_BRASIL,
  tamanhoMarcador,
  zoomDaRegiao,
} from './agrupamento';

const rio = { id_ibge: 3304557, nome: 'Rio de Janeiro', uf: 'RJ' };

describe('agrupamento do mapa', () => {
  const itens = [
    item(1),
    item(2, { quantidade: { toneladas: null, litros: 50, unidades: null } }),
    item(3, {
      gerador: { cnpj: '33333333000133', razao_social: 'Rio Ltda', municipio: rio },
      localizacao: { lat: -22.9, lon: -43.2, precisao: 'municipio' },
    }),
  ];

  it('junta os geradores do mesmo município e soma as toneladas', () => {
    const pontos = agruparPorMunicipio(itens);
    expect(pontos).toHaveLength(2);
    const sp = pontos.find((p) => p.chave === '3550308');
    expect(sp?.itens).toHaveLength(2);
    expect(sp?.toneladas).toBeCloseTo(15.001);
  });

  it('agrupa municípios próximos no zoom do Brasil e separa no zoom alto', () => {
    const indice = criarIndice(agruparPorMunicipio(itens));
    const longe = indice.marcadores(bboxDaRegiao(REGIAO_BRASIL), zoomDaRegiao(REGIAO_BRASIL));
    expect(longe).toHaveLength(1);
    expect(longe[0]).toMatchObject({ tipo: 'grupo', geradores: 3 });
    const perto = indice.marcadores([-50, -25, -40, -20], 10);
    expect(perto.map((m) => m.tipo)).toEqual(['municipio', 'municipio']);
  });

  it('marcador cresce com a quantidade', () => {
    expect(tamanhoMarcador(0)).toBe(28);
    expect(tamanhoMarcador(1000)).toBeGreaterThan(tamanhoMarcador(10));
    expect(tamanhoMarcador(1e12)).toBe(60);
  });
});
