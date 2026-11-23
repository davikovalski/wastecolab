import {
  FILTROS_PADRAO,
  type Filtros,
  lerFiltros,
  paraConsulta,
  paraParams,
  proximoRaio,
  temFiltrosAtivos,
} from './filtros';

const definidos = (p: Record<string, string | undefined>) =>
  Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined));

describe('filtros na URL', () => {
  it('sem parâmetros usa o padrão (Brasil, 100 km, por quantidade)', () => {
    expect(lerFiltros({})).toEqual(FILTROS_PADRAO);
    expect(definidos(paraParams(FILTROS_PADRAO))).toEqual({});
  });

  it('ida e volta mantém os filtros', () => {
    const filtros: Filtros = {
      localizacao: { tipo: 'municipio', id: 3550308, nome: 'São Paulo', uf: 'SP' },
      residuo: { codigo: '070213', descricao: 'Resíduos de plásticos' },
      perigoso: false,
      raioKm: 250,
      ordem: 'distancia',
    };
    expect(lerFiltros(paraParams(filtros))).toEqual(filtros);
  });

  it('GPS arredonda para 2 casas (chave de cache estável)', () => {
    const f = lerFiltros(
      paraParams({ ...FILTROS_PADRAO, localizacao: { tipo: 'gps', lat: -23.55123, lon: -46.63456 } }),
    );
    expect(f.localizacao).toEqual({ tipo: 'gps', lat: -23.55, lon: -46.63 });
    expect(paraConsulta(f)).toMatchObject({ lat: -23.55, lon: -46.63, raio_local_km: 50 });
  });

  it('valores inválidos voltam ao padrão em vez de gerar 422', () => {
    const f = lerFiltros({
      raio: '30',
      uf: 'XX',
      residuo: '12',
      perigoso: 'talvez',
      ordem: 'nome',
      lat: '999',
      lon: '0',
    });
    expect(f).toEqual(FILTROS_PADRAO);
  });

  it('aceita UF minúscula e município só com UF válida', () => {
    expect(lerFiltros({ uf: 'rs' }).localizacao).toEqual({ tipo: 'uf', uf: 'RS' });
    expect(lerFiltros({ municipio: '3550308' }).localizacao).toEqual({ tipo: 'brasil' });
  });

  it('monta a consulta da API só com o que foi filtrado', () => {
    expect(paraConsulta(FILTROS_PADRAO)).toEqual({ raio_km: 100, ordem: 'quantidade' });
    expect(paraConsulta(lerFiltros({ uf: 'SP', perigoso: 'sim', residuo: '070213' }))).toEqual({
      raio_km: 100,
      ordem: 'quantidade',
      uf: 'SP',
      perigoso: true,
      codigo_residuo: '070213',
    });
  });

  it('próximo raio e filtros ativos', () => {
    expect(proximoRaio(100)).toBe(250);
    expect(proximoRaio(500)).toBeNull();
    expect(temFiltrosAtivos(FILTROS_PADRAO)).toBe(false);
    expect(temFiltrosAtivos({ ...FILTROS_PADRAO, perigoso: true })).toBe(true);
  });
});
