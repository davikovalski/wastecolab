import { FlashList } from '@shopify/flash-list';
import { ActivityIndicator, RefreshControl, Text, View } from 'react-native';

import type { OportunidadeItem } from '@/api/tipos';
import { Botao } from '@/components/ui/Botao';
import { DataAtualizacao } from '@/components/ui/DataAtualizacao';
import { EstadoConsulta } from '@/components/ui/EstadoConsulta';
import { SkeletonLista } from '@/components/ui/Skeleton';
import { useFiltros } from '@/features/filtros/useFiltros';
import { pluralizar } from '@/lib/formatar';

import { CartaoOportunidade } from './CartaoOportunidade';
import { SemResultados } from './SemResultados';
import { useOportunidades } from './useOportunidades';

/** HU1: lista paginada com loading, vazio, erro e offline. */
export function ListaOportunidades() {
  const { filtros } = useFiltros();
  const consulta = useOportunidades(filtros);
  const { itens, total } = consulta;

  return (
    <EstadoConsulta consulta={consulta} carregando={<SkeletonLista />}>
      {itens.length === 0 ? (
        <SemResultados />
      ) : (
        <FlashList<OportunidadeItem>
          testID="lista-oportunidades"
          data={itens}
          keyExtractor={(item) => `${item.gerador.cnpj}-${item.residuo.codigo}`}
          renderItem={({ item }) => <CartaoOportunidade item={item} raioKm={filtros.raioKm} />}
          contentContainerStyle={{ paddingBottom: 96 }}
          ListHeaderComponent={
            <View className="flex-row items-baseline justify-between px-4 pb-2 pt-3">
              <Text className="text-sm font-semibold text-slate-700">
                {pluralizar(total, 'oportunidade', 'oportunidades')}
              </Text>
              <DataAtualizacao momento={consulta.dataUpdatedAt} />
            </View>
          }
          onEndReachedThreshold={0.5}
          onEndReached={() => {
            if (consulta.hasNextPage && !consulta.isFetchingNextPage && !consulta.isFetchNextPageError) {
              void consulta.fetchNextPage();
            }
          }}
          ListFooterComponent={
            consulta.isFetchingNextPage ? (
              <ActivityIndicator className="my-4" color="#0F766E" />
            ) : consulta.isFetchNextPageError ? (
              <View className="mx-4 my-2">
                <Text className="mb-2 text-center text-sm text-slate-600">Não deu para carregar mais itens.</Text>
                <Botao titulo="Tentar novamente" variante="secundario" onPress={() => void consulta.fetchNextPage()} />
              </View>
            ) : null
          }
          refreshControl={
            <RefreshControl
              refreshing={consulta.isRefetching && !consulta.isFetchingNextPage}
              onRefresh={() => void consulta.refetch()}
              tintColor="#0F766E"
            />
          }
        />
      )}
    </EstadoConsulta>
  );
}
