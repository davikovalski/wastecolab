/**
 * Agrupamento do mapa (HU2, critério 2). A posição de cada gerador é o centro do município, então
 * primeiro juntamos os geradores por município e depois agrupamos os municípios próximos (supercluster)
 * conforme o zoom.
 */
import Supercluster from 'supercluster';

import type { OportunidadeItem } from '@/api/tipos';

export interface PontoMunicipio {
  chave: string;
  nome: string;
  lat: number;
  lon: number;
  toneladas: number;
  itens: OportunidadeItem[];
}

export function agruparPorMunicipio(itens: readonly OportunidadeItem[]): PontoMunicipio[] {
  const grupos = new Map<string, PontoMunicipio>();
  for (const item of itens) {
    const m = item.gerador.municipio;
    const chave = m ? String(m.id_ibge) : `${item.localizacao.lat},${item.localizacao.lon}`;
    const existente = grupos.get(chave);
    if (existente) {
      existente.itens.push(item);
      existente.toneladas += item.quantidade.toneladas ?? 0;
    } else {
      grupos.set(chave, {
        chave,
        nome: m ? `${m.nome}/${m.uf}` : 'Município não informado',
        lat: item.localizacao.lat,
        lon: item.localizacao.lon,
        toneladas: item.quantidade.toneladas ?? 0,
        itens: [item],
      });
    }
  }
  return [...grupos.values()];
}

interface Propriedades {
  chave: string;
  toneladas: number;
  geradores: number;
}
type Resumo = Pick<Propriedades, 'toneladas' | 'geradores'>;

export type Marcador =
  | { tipo: 'grupo'; id: number; lat: number; lon: number; toneladas: number; geradores: number }
  | { tipo: 'municipio'; ponto: PontoMunicipio };

export interface IndiceMapa {
  marcadores: (bbox: [number, number, number, number], zoom: number) => Marcador[];
  zoomParaAbrir: (idGrupo: number) => number;
}

export function criarIndice(pontos: readonly PontoMunicipio[]): IndiceMapa {
  const porChave = new Map(pontos.map((p) => [p.chave, p]));
  const indice = new Supercluster<Propriedades, Resumo>({
    radius: 60,
    maxZoom: 9,
    map: (p) => ({ toneladas: p.toneladas, geradores: p.geradores }),
    reduce: (acumulado, p) => {
      acumulado.toneladas += p.toneladas;
      acumulado.geradores += p.geradores;
    },
  });
  indice.load(
    pontos.map((p) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
      properties: { chave: p.chave, toneladas: p.toneladas, geradores: p.itens.length },
    })),
  );

  return {
    marcadores: (bbox, zoom) =>
      indice.getClusters(bbox, Math.round(zoom)).flatMap((f): Marcador[] => {
        const [lon, lat] = f.geometry.coordinates;
        if (lon === undefined || lat === undefined) return [];
        if ('cluster' in f.properties && f.properties.cluster) {
          const { cluster_id, toneladas, geradores } = f.properties;
          return [{ tipo: 'grupo', id: cluster_id, lat, lon, toneladas, geradores }];
        }
        const ponto = 'chave' in f.properties ? porChave.get(f.properties.chave) : undefined;
        return ponto ? [{ tipo: 'municipio', ponto }] : [];
      }),
    zoomParaAbrir: (idGrupo) => indice.getClusterExpansionZoom(idGrupo),
  };
}

/** Diâmetro em px: cresce com a quantidade, em escala logarítmica para não esconder os pequenos. */
export function tamanhoMarcador(toneladas: number): number {
  return Math.round(28 + Math.min(32, 8 * Math.log10(1 + Math.max(0, toneladas))));
}

export interface Regiao {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
}

export function zoomDaRegiao(r: Regiao): number {
  return Math.max(0, Math.min(20, Math.log2(360 / Math.max(r.longitudeDelta, 1e-6))));
}

export function bboxDaRegiao(r: Regiao): [number, number, number, number] {
  return [
    r.longitude - r.longitudeDelta / 2,
    r.latitude - r.latitudeDelta / 2,
    r.longitude + r.longitudeDelta / 2,
    r.latitude + r.latitudeDelta / 2,
  ];
}

export function regiaoComZoom(lat: number, lon: number, zoom: number): Regiao {
  const delta = 360 / 2 ** zoom;
  return { latitude: lat, longitude: lon, latitudeDelta: delta, longitudeDelta: delta };
}

export const REGIAO_BRASIL: Regiao = { latitude: -14.2, longitude: -51.9, latitudeDelta: 38, longitudeDelta: 38 };
