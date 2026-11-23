import { View } from 'react-native';

import { BarraFiltros } from '@/features/filtros/BarraFiltros';
import { MapaOportunidades } from '@/features/oportunidades/MapaOportunidades';

/** HU2: mapa com os mesmos filtros da lista. */
export default function TelaMapa() {
  return (
    <View className="flex-1">
      <BarraFiltros visao="mapa" />
      <MapaOportunidades />
    </View>
  );
}
