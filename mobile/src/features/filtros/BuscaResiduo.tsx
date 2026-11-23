import { useState } from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';

import { mensagemDoErro } from '@/api/erros';
import { Botao } from '@/components/ui/Botao';
import { formatarCodigoResiduo, formatarPerigoso } from '@/lib/formatar';

import type { ResiduoFiltro } from './filtros';
import { useBuscaResiduos } from './useBuscas';

interface Props {
  selecionado: ResiduoFiltro | null;
  perigoso: boolean | null;
  onSelecionar: (residuo: ResiduoFiltro | null) => void;
}

/** Busca de resíduo por código ("0702") ou descrição ("plástico"), sem acento. */
export function BuscaResiduo({ selecionado, perigoso, onSelecionar }: Props) {
  const [texto, setTexto] = useState('');
  const busca = useBuscaResiduos(texto, perigoso);

  if (selecionado) {
    return (
      <View className="flex-row items-center rounded-lg border border-marca bg-marca-claro px-3 py-2.5">
        <Text className="flex-1 text-sm text-marca-escuro" numberOfLines={2}>
          {formatarCodigoResiduo(selecionado.codigo)} · {selecionado.descricao}
        </Text>
        <Pressable accessibilityRole="button" accessibilityLabel="Remover resíduo" onPress={() => onSelecionar(null)}>
          <Text className="px-2 text-lg text-marca-escuro">✕</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View>
      <TextInput
        value={texto}
        onChangeText={setTexto}
        placeholder="Código ou descrição, ex.: 0702 ou plástico"
        autoCorrect={false}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-base text-slate-900"
        accessibilityLabel="Buscar resíduo"
      />
      <View className="mt-2 max-h-64">
        {busca.isPending && busca.fetchStatus !== 'paused' ? (
          <ActivityIndicator className="my-3" color="#0F766E" />
        ) : busca.isError && busca.data === undefined ? (
          <View className="py-2">
            <Text className="mb-2 text-sm text-slate-600">{mensagemDoErro(busca.error)}</Text>
            <Botao titulo="Tentar de novo" variante="secundario" onPress={() => void busca.refetch()} />
          </View>
        ) : busca.data && busca.data.length === 0 ? (
          <Text className="py-3 text-sm text-slate-600">Nada encontrado.</Text>
        ) : (
          busca.data?.slice(0, 8).map((r) => (
            <Pressable
              key={r.codigo}
              accessibilityRole="button"
              onPress={() => onSelecionar({ codigo: r.codigo, descricao: r.descricao })}
              className="border-b border-slate-100 py-2.5 active:bg-slate-50"
            >
              <Text className="text-sm text-slate-900" numberOfLines={2}>
                <Text className="font-semibold">{formatarCodigoResiduo(r.codigo)}</Text> · {r.descricao}
              </Text>
              <Text className="text-xs text-slate-500">
                {formatarPerigoso(r.perigoso)} · {r.oportunidades} oportunidade{r.oportunidades === 1 ? '' : 's'}
              </Text>
            </Pressable>
          ))
        )}
      </View>
    </View>
  );
}
