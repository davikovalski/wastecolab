import { useState } from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';

import { mensagemDoErro } from '@/api/erros';
import type { Municipio } from '@/api/tipos';
import { Botao } from '@/components/ui/Botao';

import { useBuscaMunicipios } from './useBuscas';

interface Props {
  uf: string | null;
  onSelecionar: (municipio: Municipio) => void;
}

export function BuscaMunicipio({ uf, onSelecionar }: Props) {
  const [texto, setTexto] = useState('');
  const busca = useBuscaMunicipios(texto, uf);
  const digitou = texto.trim().length >= 2;

  return (
    <View>
      <TextInput
        value={texto}
        onChangeText={setTexto}
        placeholder={uf ? `Município em ${uf}` : 'Município (digite 2 letras ou mais)'}
        autoCorrect={false}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-base text-slate-900"
        accessibilityLabel="Buscar município"
      />
      {digitou ? (
        <View className="mt-2">
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
            busca.data?.slice(0, 6).map((m) => (
              <Pressable
                key={m.id_ibge}
                accessibilityRole="button"
                onPress={() => {
                  onSelecionar(m);
                  setTexto('');
                }}
                className="border-b border-slate-100 py-2.5 active:bg-slate-50"
              >
                <Text className="text-sm text-slate-900">
                  {m.nome}/{m.uf}
                </Text>
              </Pressable>
            ))
          )}
        </View>
      ) : null}
    </View>
  );
}
