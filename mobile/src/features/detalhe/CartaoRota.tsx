import { Text, View } from 'react-native';

import type { Rota } from '@/api/tipos';
import { formatarCnpj, formatarKm, formatarQuantidadeCompleta, NAO_INFORMADO } from '@/lib/formatar';

import { ContextoMunicipal } from './ContextoMunicipal';

/** Um destinador candidato (HU3, critério 2). */
export function CartaoRota({ rota }: { rota: Rota }) {
  const { destinador } = rota;
  const municipio = destinador.municipio ? `${destinador.municipio.nome}/${destinador.municipio.uf}` : NAO_INFORMADO;
  return (
    <View className="mx-4 mb-3 rounded-xl border border-slate-200 bg-white p-4">
      <View className="flex-row items-start justify-between gap-3">
        <View className="flex-1">
          <Text className="text-base font-semibold text-slate-900">{destinador.razao_social}</Text>
          <Text className="text-xs text-slate-500">
            CNPJ {formatarCnpj(destinador.cnpj)} · {municipio}
          </Text>
        </View>
        <Text className="rounded-md bg-marca-claro px-2 py-1 text-sm font-bold text-marca-escuro">
          {formatarKm(rota.distancia_km)}
        </Text>
      </View>

      <View className="mt-3 gap-1">
        {rota.operacoes.map((o) => (
          <Text key={o.codigo} className="text-sm text-slate-800">
            <Text className="font-semibold text-marca">{o.codigo}</Text> – {o.descricao}
          </Text>
        ))}
        <Text className="text-sm text-slate-700">
          Já recebeu: {formatarQuantidadeCompleta(rota.quantidade_recebida)} em {rota.ano_mais_recente}
        </Text>
      </View>

      <View className="mt-3 border-t border-slate-100 pt-2">
        <ContextoMunicipal contexto={rota.contexto_municipal} />
      </View>
    </View>
  );
}
