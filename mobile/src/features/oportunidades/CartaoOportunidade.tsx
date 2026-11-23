import { Link } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import type { OportunidadeItem } from '@/api/tipos';
import type { RaioKm } from '@/lib/constantes';
import {
  formatarCodigoResiduo,
  formatarKm,
  formatarPerigoso,
  formatarQuantidade,
  NAO_INFORMADO,
  pluralizar,
} from '@/lib/formatar';

interface Props {
  item: OportunidadeItem;
  raioKm: RaioKm;
}

export function rotaDetalhe(item: OportunidadeItem, raioKm: RaioKm) {
  return {
    pathname: '/oportunidade/[cnpj]/[codigo]',
    params: { cnpj: item.gerador.cnpj, codigo: item.residuo.codigo, raio: String(raioKm) },
  } as const;
}

/** Item da lista (HU1, critério 2). */
export function CartaoOportunidade({ item, raioKm }: Props) {
  const { gerador, residuo, rotas } = item;
  const municipio = gerador.municipio ? `${gerador.municipio.nome}/${gerador.municipio.uf}` : NAO_INFORMADO;
  const operacoes = item.operacoes_atuais.map((o) => `${o.codigo} – ${o.descricao}`).join(' · ');

  return (
    <Link href={rotaDetalhe(item, raioKm)} asChild>
      <Pressable
        accessibilityRole="button"
        className="mx-4 mb-3 rounded-xl border border-slate-200 bg-white p-4 active:bg-slate-50"
      >
        <Text className="text-base font-semibold text-slate-900" numberOfLines={2}>
          {gerador.razao_social}
        </Text>
        <Text className="mb-3 text-sm text-slate-500">{municipio}</Text>

        <Text className="text-sm text-slate-800" numberOfLines={2}>
          <Text className="font-semibold">{formatarCodigoResiduo(residuo.codigo)}</Text> · {residuo.descricao}
        </Text>
        <View className="mt-1 flex-row flex-wrap items-center gap-x-3">
          <Text className="text-sm font-semibold text-slate-900">{formatarQuantidade(item.quantidade)}</Text>
          <Text className="text-sm text-slate-500">em {item.ano}</Text>
          {residuo.perigoso ? (
            <Text className="rounded bg-red-50 px-1.5 text-xs font-semibold text-red-700">
              {formatarPerigoso(residuo.perigoso)}
            </Text>
          ) : null}
        </View>

        <Text className="mt-2 text-xs text-aterro" numberOfLines={2}>
          Hoje: {operacoes || NAO_INFORMADO}
        </Text>

        <View className="mt-3 rounded-lg bg-marca-claro px-3 py-2">
          <Text className="text-sm font-semibold text-marca-escuro">
            {pluralizar(rotas.total, 'destinador valorizador', 'destinadores valorizadores')} em até {raioKm} km
          </Text>
          <Text className="text-xs text-marca-escuro">
            Mais próximo a {formatarKm(rotas.distancia_mais_proxima_km)}
          </Text>
        </View>
      </Pressable>
    </Link>
  );
}
