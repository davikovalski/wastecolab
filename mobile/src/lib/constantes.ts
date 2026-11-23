export const API_URL: string = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Raios pré-calculados no banco. Qualquer outro valor é recusado pela API. */
export const RAIOS_KM = [25, 50, 100, 250, 500] as const;
export type RaioKm = (typeof RAIOS_KM)[number];
export const RAIO_PADRAO_KM: RaioKm = 100;

export const POR_PAGINA = 20;
/** Área em volta da posição do GPS (o padrão da API). */
export const RAIO_LOCAL_KM = 50;

export const TIMEOUT_MS = 15_000;
/** Igual ao `max-age` da API. */
export const DADOS_FRESCOS_MS = 5 * 60 * 1000;
/** Quanto tempo o último resultado fica guardado para o modo offline. */
export const CACHE_OFFLINE_MS = 7 * 24 * 60 * 60 * 1000;

export const UFS = [
  'AC',
  'AL',
  'AM',
  'AP',
  'BA',
  'CE',
  'DF',
  'ES',
  'GO',
  'MA',
  'MG',
  'MS',
  'MT',
  'PA',
  'PB',
  'PE',
  'PI',
  'PR',
  'RJ',
  'RN',
  'RO',
  'RR',
  'RS',
  'SC',
  'SE',
  'SP',
  'TO',
] as const;
export type Uf = (typeof UFS)[number];
