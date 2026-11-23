/**
 * Filtros da busca (HU1). Ficam nos search params da URL: lista e mapa leem os mesmos parâmetros,
 * então alternar entre as telas mantém os filtros e reaproveita a mesma consulta em cache.
 */
import type { Ordem } from '@/api/tipos';
import { RAIO_LOCAL_KM, RAIO_PADRAO_KM, RAIOS_KM, type RaioKm, UFS, type Uf } from '@/lib/constantes';

export type Localizacao =
  | { tipo: 'brasil' }
  | { tipo: 'uf'; uf: Uf }
  | { tipo: 'municipio'; id: number; nome: string; uf: Uf }
  | { tipo: 'gps'; lat: number; lon: number };

export interface ResiduoFiltro {
  codigo: string;
  descricao: string;
}

export interface Filtros {
  localizacao: Localizacao;
  residuo: ResiduoFiltro | null;
  perigoso: boolean | null;
  raioKm: RaioKm;
  ordem: Ordem;
}

export const FILTROS_PADRAO: Filtros = {
  localizacao: { tipo: 'brasil' },
  residuo: null,
  perigoso: null,
  raioKm: RAIO_PADRAO_KM,
  ordem: 'quantidade',
};

/** Parâmetros como chegam do Expo Router. */
export type ParamsUrl = Record<string, string | string[] | undefined>;
/** Todas as chaves que os filtros usam na URL (`undefined` remove a chave). */
export type ParamsFiltros = Record<
  'uf' | 'municipio' | 'municipio_nome' | 'lat' | 'lon' | 'residuo' | 'residuo_nome' | 'perigoso' | 'raio' | 'ordem',
  string | undefined
>;

function primeiro(valor: string | string[] | undefined): string | undefined {
  const v = Array.isArray(valor) ? valor[0] : valor;
  return v === undefined || v === '' ? undefined : v;
}

function numeroOuNulo(valor: string | undefined): number | null {
  if (valor === undefined) return null;
  const n = Number(valor);
  return Number.isFinite(n) ? n : null;
}

export function ehUf(valor: string | undefined): valor is Uf {
  return valor !== undefined && (UFS as readonly string[]).includes(valor);
}

export function ehRaio(valor: number | null): valor is RaioKm {
  return valor !== null && (RAIOS_KM as readonly number[]).includes(valor);
}

function lerLocalizacao(p: ParamsUrl): Localizacao {
  const lat = numeroOuNulo(primeiro(p.lat));
  const lon = numeroOuNulo(primeiro(p.lon));
  if (lat !== null && lon !== null && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
    return { tipo: 'gps', lat, lon };
  }
  const uf = primeiro(p.uf)?.toUpperCase();
  const municipio = numeroOuNulo(primeiro(p.municipio));
  if (municipio !== null && municipio >= 1_000_000 && municipio <= 9_999_999 && ehUf(uf)) {
    return { tipo: 'municipio', id: municipio, nome: primeiro(p.municipio_nome) ?? String(municipio), uf };
  }
  if (ehUf(uf)) return { tipo: 'uf', uf };
  return { tipo: 'brasil' };
}

/** Lê a URL de forma tolerante: valor inválido volta ao padrão em vez de gerar erro 422. */
export function lerFiltros(p: ParamsUrl): Filtros {
  const codigo = primeiro(p.residuo);
  const perigoso = primeiro(p.perigoso);
  const raio = numeroOuNulo(primeiro(p.raio));
  return {
    localizacao: lerLocalizacao(p),
    residuo:
      codigo !== undefined && /^\d{6}$/.test(codigo) ? { codigo, descricao: primeiro(p.residuo_nome) ?? codigo } : null,
    perigoso: perigoso === 'sim' ? true : perigoso === 'nao' ? false : null,
    raioKm: ehRaio(raio) ? raio : RAIO_PADRAO_KM,
    ordem: primeiro(p.ordem) === 'distancia' ? 'distancia' : 'quantidade',
  };
}

/** Coordenadas com 2 casas (~1 km): a chave do cache não muda a cada leitura do GPS. */
export function arredondarCoordenada(valor: number): number {
  return Math.round(valor * 100) / 100;
}

export function paraParams(f: Filtros): ParamsFiltros {
  const l = f.localizacao;
  return {
    uf: l.tipo === 'uf' || l.tipo === 'municipio' ? l.uf : undefined,
    municipio: l.tipo === 'municipio' ? String(l.id) : undefined,
    municipio_nome: l.tipo === 'municipio' ? l.nome : undefined,
    lat: l.tipo === 'gps' ? String(arredondarCoordenada(l.lat)) : undefined,
    lon: l.tipo === 'gps' ? String(arredondarCoordenada(l.lon)) : undefined,
    residuo: f.residuo?.codigo,
    residuo_nome: f.residuo?.descricao,
    perigoso: f.perigoso === null ? undefined : f.perigoso ? 'sim' : 'nao',
    raio: f.raioKm === RAIO_PADRAO_KM ? undefined : String(f.raioKm),
    ordem: f.ordem === 'quantidade' ? undefined : f.ordem,
  };
}

/** Parâmetros de `GET /v1/oportunidades` (sem paginação). Também é a chave do cache. */
export interface ConsultaOportunidades {
  raio_km: RaioKm;
  uf?: string;
  municipio_id?: number;
  lat?: number;
  lon?: number;
  raio_local_km?: number;
  codigo_residuo?: string;
  perigoso?: boolean;
  ordem: Ordem;
}

export function paraConsulta(f: Filtros): ConsultaOportunidades {
  const l = f.localizacao;
  const consulta: ConsultaOportunidades = { raio_km: f.raioKm, ordem: f.ordem };
  if (l.tipo === 'uf') consulta.uf = l.uf;
  if (l.tipo === 'municipio') consulta.municipio_id = l.id;
  if (l.tipo === 'gps') {
    consulta.lat = arredondarCoordenada(l.lat);
    consulta.lon = arredondarCoordenada(l.lon);
    consulta.raio_local_km = RAIO_LOCAL_KM;
  }
  if (f.residuo) consulta.codigo_residuo = f.residuo.codigo;
  if (f.perigoso !== null) consulta.perigoso = f.perigoso;
  return consulta;
}

/** Próximo raio da lista (para o botão "Aumentar raio"), ou `null` se já está no maior. */
export function proximoRaio(atual: RaioKm): RaioKm | null {
  const i = RAIOS_KM.indexOf(atual);
  return RAIOS_KM[i + 1] ?? null;
}

export function temFiltrosAtivos(f: Filtros): boolean {
  return f.localizacao.tipo !== 'brasil' || f.residuo !== null || f.perigoso !== null || f.raioKm !== RAIO_PADRAO_KM;
}

export function descreverLocalizacao(l: Localizacao): string {
  switch (l.tipo) {
    case 'brasil':
      return 'Todo o Brasil';
    case 'uf':
      return l.uf;
    case 'municipio':
      return `${l.nome}/${l.uf}`;
    case 'gps':
      return `Perto de mim (${RAIO_LOCAL_KM} km)`;
  }
}
