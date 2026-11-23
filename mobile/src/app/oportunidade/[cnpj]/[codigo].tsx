import { router, useLocalSearchParams } from 'expo-router';

import { EmptyState } from '@/components/ui/EmptyState';
import { Botao } from '@/components/ui/Botao';
import { TelaDetalhe } from '@/features/detalhe/TelaDetalhe';
import { ehRaio } from '@/features/filtros/filtros';
import { RAIO_PADRAO_KM } from '@/lib/constantes';

type Params = { cnpj?: string; codigo?: string; raio?: string };

/** HU3: detalhe da oportunidade. O raio vem da lista/mapa para mostrar os mesmos destinadores. */
export default function TelaOportunidade() {
  const { cnpj, codigo, raio } = useLocalSearchParams<Params>();
  const raioNumero = raio === undefined ? null : Number(raio);
  const raioKm = ehRaio(raioNumero) ? raioNumero : RAIO_PADRAO_KM;

  if (!cnpj || !/^\d{14}$/.test(cnpj) || !codigo || !/^\d{6}$/.test(codigo)) {
    return (
      <EmptyState titulo="Link inválido" descricao="Esta oportunidade não existe.">
        <Botao titulo="Voltar" onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} />
      </EmptyState>
    );
  }

  return (
    <TelaDetalhe
      cnpj={cnpj}
      codigo={codigo}
      raioKm={raioKm}
      onMudarRaio={(novo) => router.setParams({ raio: String(novo) })}
    />
  );
}
