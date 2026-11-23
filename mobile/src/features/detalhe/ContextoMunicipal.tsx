import { Linking, Pressable, Text, View } from 'react-native';

import type { ContextoMunicipal as Contexto, Meta } from '@/api/tipos';
import { formatarNumero, formatarSimNao, NAO_INFORMADO } from '@/lib/formatar';

const NOMES_META: Record<string, string> = {
  coleta_seletiva: 'Coleta seletiva',
  reciclagem: 'Reciclagem',
  reducao: 'Redução',
  reutilizacao: 'Reutilização',
  eliminacao_lixoes: 'Eliminação de lixões',
};

function descreverMeta(m: Meta): string {
  const atual = m.valor_atual == null ? NAO_INFORMADO : `${formatarNumero(m.valor_atual)}%`;
  const alvo = m.valor_meta == null ? NAO_INFORMADO : `${formatarNumero(m.valor_meta)}%`;
  const prazo = m.prazo_ano ?? m.prazo_texto ?? NAO_INFORMADO;
  return `${NOMES_META[m.tipo] ?? m.tipo}: hoje ${atual}, meta ${alvo} até ${prazo}`;
}

/** Resumo do diagnóstico municipal do destinador (HU3, critério 3). */
export function ContextoMunicipal({ contexto }: { contexto: Contexto | null }) {
  if (!contexto) {
    return <Text className="text-xs italic text-slate-500">Município sem diagnóstico</Text>;
  }
  return (
    <View className="gap-0.5">
      <Text className="text-xs text-slate-600">
        Diagnóstico {contexto.ano_referencia} · Coleta seletiva: {formatarSimNao(contexto.possui_coleta_seletiva)}
      </Text>
      <View className="flex-row flex-wrap items-center">
        <Text className="text-xs text-slate-600">
          Plano de gestão: {formatarSimNao(contexto.possui_plano_gestao)}
          {contexto.ano_ultima_versao_plano ? ` (versão de ${contexto.ano_ultima_versao_plano})` : ''}
        </Text>
        {contexto.link_plano ? (
          <Pressable
            accessibilityRole="link"
            onPress={() => void Linking.openURL(contexto.link_plano ?? '')}
            hitSlop={8}
          >
            <Text className="ml-1 text-xs font-semibold text-marca underline">abrir plano</Text>
          </Pressable>
        ) : null}
      </View>
      {contexto.metas.map((m, i) => (
        <Text key={`${m.tipo}-${i}`} className="text-xs text-slate-600">
          {descreverMeta(m)}
        </Text>
      ))}
    </View>
  );
}
