/**
 * Formatação única de valores vindos da API.
 * Campos `null` sempre viram "Não informado", nunca 0.
 */
import type { Quantidade } from '@/api/tipos';

export const NAO_INFORMADO = 'Não informado';

const numero = (casas: number) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: casas });

export function formatarNumero(valor: number | null | undefined, casas = 1): string {
  return valor == null ? NAO_INFORMADO : numero(casas).format(valor);
}

export function formatarToneladas(valor: number | null | undefined): string {
  if (valor == null) return NAO_INFORMADO;
  return `${numero(valor < 10 ? 2 : 1).format(valor)} t`;
}

export function formatarLitros(valor: number | null | undefined): string {
  return valor == null ? NAO_INFORMADO : `${numero(0).format(valor)} L`;
}

export function formatarUnidades(valor: number | null | undefined): string {
  return valor == null ? NAO_INFORMADO : `${numero(0).format(valor)} un.`;
}

/** Quantidade principal: toneladas, senão litros, senão unidades. */
export function formatarQuantidade(q: Quantidade): string {
  if (q.toneladas != null) return formatarToneladas(q.toneladas);
  if (q.litros != null) return formatarLitros(q.litros);
  if (q.unidades != null) return formatarUnidades(q.unidades);
  return NAO_INFORMADO;
}

/** Todas as unidades informadas, ex.: "15 t · 200 L". */
export function formatarQuantidadeCompleta(q: Quantidade): string {
  const partes = [
    q.toneladas != null ? formatarToneladas(q.toneladas) : null,
    q.litros != null ? formatarLitros(q.litros) : null,
    q.unidades != null ? formatarUnidades(q.unidades) : null,
  ].filter((p): p is string => p !== null);
  return partes.length > 0 ? partes.join(' · ') : NAO_INFORMADO;
}

export function formatarKm(valor: number | null | undefined): string {
  if (valor == null) return NAO_INFORMADO;
  if (valor < 1) return 'menos de 1 km';
  return `${numero(valor < 10 ? 1 : 0).format(valor)} km`;
}

export function formatarCnpj(cnpj: string | null | undefined): string {
  if (!cnpj) return NAO_INFORMADO;
  const d = cnpj.replace(/\D/g, '');
  if (d.length !== 14) return cnpj;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

export function formatarCodigoResiduo(codigo: string): string {
  // Lista Brasileira de Resíduos: "070213" → "07 02 13"
  return /^\d{6}$/.test(codigo) ? `${codigo.slice(0, 2)} ${codigo.slice(2, 4)} ${codigo.slice(4)}` : codigo;
}

export function formatarPerigoso(perigoso: boolean | null | undefined): string {
  if (perigoso == null) return NAO_INFORMADO;
  return perigoso ? 'Perigoso' : 'Não perigoso';
}

export function formatarTexto(valor: string | null | undefined): string {
  return valor == null || valor.trim() === '' ? NAO_INFORMADO : valor;
}

export function formatarSimNao(valor: boolean | null | undefined): string {
  if (valor == null) return NAO_INFORMADO;
  return valor ? 'Sim' : 'Não';
}

const dois = (n: number) => String(n).padStart(2, '0');

/** "23/11, 09:40" (hora local do aparelho). */
export function formatarDataHora(momento: number | Date): string {
  const d = typeof momento === 'number' ? new Date(momento) : momento;
  return `${dois(d.getDate())}/${dois(d.getMonth() + 1)}, ${dois(d.getHours())}:${dois(d.getMinutes())}`;
}

/** "2026-03-01" → "01/03/2026". Datas sem hora não passam por fuso horário. */
export function formatarData(iso: string | null | undefined): string {
  if (!iso) return NAO_INFORMADO;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}

export function pluralizar(n: number, singular: string, plural: string): string {
  return `${numero(0).format(n)} ${n === 1 ? singular : plural}`;
}
