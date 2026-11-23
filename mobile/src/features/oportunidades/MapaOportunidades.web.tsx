import { EmptyState } from '@/components/ui/EmptyState';
import { Botao } from '@/components/ui/Botao';
import { useFiltros } from '@/features/filtros/useFiltros';

/** O react-native-maps não roda no navegador: a versão web (só para verificação) aponta para a lista. */
export function MapaOportunidades() {
  const { irPara } = useFiltros();
  return (
    <EmptyState titulo="Mapa disponível no aplicativo" descricao="No navegador, use a lista de oportunidades.">
      <Botao titulo="Ver em lista" onPress={() => irPara('lista')} />
    </EmptyState>
  );
}
