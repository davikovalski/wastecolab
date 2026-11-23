import { Text } from 'react-native';

import { formatarDataHora } from '@/lib/formatar';

/** "Dados de 23/11, 09:40": quando este resultado foi buscado na API. */
export function DataAtualizacao({ momento }: { momento: number }) {
  if (momento <= 0) return null;
  return <Text className="text-xs text-slate-500">Dados de {formatarDataHora(momento)}</Text>;
}
