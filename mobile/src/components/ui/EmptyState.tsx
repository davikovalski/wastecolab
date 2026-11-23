import type { ReactNode } from 'react';
import { Text, View } from 'react-native';

interface Props {
  titulo: string;
  descricao?: string;
  children?: ReactNode;
}

/** Estado vazio com ações (ex.: "Aumentar raio" e "Limpar filtros"). */
export function EmptyState({ titulo, descricao, children }: Props) {
  return (
    <View className="flex-1 items-center justify-center px-8 py-12" testID="estado-vazio">
      <Text className="mb-2 text-center text-lg font-semibold text-slate-800">{titulo}</Text>
      {descricao ? <Text className="mb-6 text-center text-base text-slate-600">{descricao}</Text> : null}
      <View className="w-full gap-3">{children}</View>
    </View>
  );
}
