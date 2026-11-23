import {
  formatarCnpj,
  formatarCodigoResiduo,
  formatarData,
  formatarDataHora,
  formatarKm,
  formatarQuantidade,
  formatarQuantidadeCompleta,
  formatarSimNao,
  formatarToneladas,
  NAO_INFORMADO,
} from './formatar';

describe('formatar', () => {
  it('mostra "Não informado" para null, nunca 0', () => {
    expect(formatarToneladas(null)).toBe(NAO_INFORMADO);
    expect(formatarKm(undefined)).toBe(NAO_INFORMADO);
    expect(formatarSimNao(null)).toBe(NAO_INFORMADO);
    expect(formatarQuantidade({ toneladas: null, litros: null, unidades: null })).toBe(NAO_INFORMADO);
    expect(formatarQuantidadeCompleta({ toneladas: null, litros: null, unidades: null })).toBe(NAO_INFORMADO);
  });

  it('mantém o zero quando ele foi informado', () => {
    expect(formatarToneladas(0)).toBe('0 t');
  });

  it('formata toneladas, litros e unidades em pt-BR', () => {
    expect(formatarToneladas(15.001)).toBe('15 t');
    expect(formatarToneladas(1681.2)).toBe('1.681,2 t');
    expect(formatarToneladas(2.345)).toBe('2,35 t');
    expect(formatarQuantidade({ toneladas: null, litros: 1200, unidades: 3 })).toBe('1.200 L');
    expect(formatarQuantidadeCompleta({ toneladas: 2, litros: null, unidades: 3 })).toBe('2 t · 3 un.');
  });

  it('formata distâncias', () => {
    expect(formatarKm(0.4)).toBe('menos de 1 km');
    expect(formatarKm(4.26)).toBe('4,3 km');
    expect(formatarKm(123.7)).toBe('124 km');
  });

  it('formata CNPJ e código de resíduo', () => {
    expect(formatarCnpj('11111111000111')).toBe('11.111.111/0001-11');
    expect(formatarCnpj('123')).toBe('123');
    expect(formatarCnpj(null)).toBe(NAO_INFORMADO);
    expect(formatarCodigoResiduo('070213')).toBe('07 02 13');
  });

  it('formata datas', () => {
    expect(formatarData('2026-03-01')).toBe('01/03/2026');
    expect(formatarData(null)).toBe(NAO_INFORMADO);
    expect(formatarDataHora(new Date(2026, 10, 23, 9, 40))).toBe('23/11, 09:40');
  });
});
