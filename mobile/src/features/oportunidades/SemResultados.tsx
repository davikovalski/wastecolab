import { Botao } from '@/components/ui/Botao';
import { EmptyState } from '@/components/ui/EmptyState';
import { proximoRaio, temFiltrosAtivos } from '@/features/filtros/filtros';
import { useFiltros } from '@/features/filtros/useFiltros';

/** Estado vazio da lista e do mapa (HU1, critério 6). */
export function SemResultados() {
  const { filtros, aplicar, limpar } = useFiltros();
  const maior = proximoRaio(filtros.raioKm);

  return (
    <EmptyState
      titulo="Nenhuma oportunidade"
      descricao={
        maior
          ? `Não achamos geradores com destinador valorizador em até ${filtros.raioKm} km com estes filtros.`
          : 'Não achamos geradores com destinador valorizador com estes filtros, nem no raio máximo.'
      }
    >
      {maior ? (
        <Botao titulo={`Aumentar raio para ${maior} km`} onPress={() => aplicar({ ...filtros, raioKm: maior })} />
      ) : null}
      {temFiltrosAtivos(filtros) ? <Botao titulo="Limpar filtros" variante="secundario" onPress={limpar} /> : null}
    </EmptyState>
  );
}
