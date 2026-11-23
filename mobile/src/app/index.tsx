import { View } from 'react-native';

import { BarraFiltros } from '@/features/filtros/BarraFiltros';
import { ListaOportunidades } from '@/features/oportunidades/ListaOportunidades';

/** HU1: lista de oportunidades. */
export default function TelaLista() {
  return (
    <View className="flex-1">
      <BarraFiltros visao="lista" />
      <ListaOportunidades />
    </View>
  );
}
