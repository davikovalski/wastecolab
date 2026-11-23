import { FlashList } from '@shopify/flash-list';
import { Linking, RefreshControl, Text, View } from 'react-native';

import type { DetalheOportunidade, Fonte, Rota } from '@/api/tipos';
import { Botao } from '@/components/ui/Botao';
import { DataAtualizacao } from '@/components/ui/DataAtualizacao';
import { EmptyState } from '@/components/ui/EmptyState';
import { EstadoConsulta } from '@/components/ui/EstadoConsulta';
import { Skeleton } from '@/components/ui/Skeleton';
import { proximoRaio } from '@/features/filtros/filtros';
import type { RaioKm } from '@/lib/constantes';
import { formatarData, pluralizar } from '@/lib/formatar';

import { CabecalhoOportunidade } from './CabecalhoOportunidade';
import { CartaoRota } from './CartaoRota';
import { useDetalhe } from './useDetalhe';

interface Props {
  cnpj: string;
  codigo: string;
  raioKm: RaioKm;
  onMudarRaio: (raio: RaioKm) => void;
}

/** HU3: gerador, destinadores por distância, contexto municipal e fontes. */
export function TelaDetalhe({ cnpj, codigo, raioKm, onMudarRaio }: Props) {
  const consulta = useDetalhe({ cnpj, codigo, raioKm });

  return (
    <EstadoConsulta consulta={consulta} carregando={<SkeletonDetalhe />}>
      {consulta.data ? (
        <Conteudo
          dados={consulta.data}
          raioKm={raioKm}
          atualizadoEm={consulta.dataUpdatedAt}
          atualizando={consulta.isRefetching}
          onAtualizar={() => void consulta.refetch()}
          onMudarRaio={onMudarRaio}
        />
      ) : null}
    </EstadoConsulta>
  );
}

interface PropsConteudo {
  dados: DetalheOportunidade;
  raioKm: RaioKm;
  atualizadoEm: number;
  atualizando: boolean;
  onAtualizar: () => void;
  onMudarRaio: (raio: RaioKm) => void;
}

function Conteudo({ dados, raioKm, atualizadoEm, atualizando, onAtualizar, onMudarRaio }: PropsConteudo) {
  const maior = proximoRaio(raioKm);
  return (
    <FlashList<Rota>
      data={dados.rotas}
      keyExtractor={(r) => r.destinador.cnpj}
      renderItem={({ item }) => <CartaoRota rota={item} />}
      contentContainerStyle={{ paddingBottom: 96 }}
      refreshControl={<RefreshControl refreshing={atualizando} onRefresh={onAtualizar} tintColor="#0F766E" />}
      ListHeaderComponent={
        <View>
          <CabecalhoOportunidade oportunidade={dados.oportunidade} />
          <View className="flex-row items-baseline justify-between px-4 pb-2 pt-4">
            <Text className="text-base font-semibold text-slate-900">
              {pluralizar(dados.rotas.length, 'destinador', 'destinadores')} em até {raioKm} km
            </Text>
            <DataAtualizacao momento={atualizadoEm} />
          </View>
        </View>
      }
      ListEmptyComponent={
        <EmptyState titulo="Nenhum destinador no raio" descricao={`Não há destinador valorizador em até ${raioKm} km.`}>
          {maior ? <Botao titulo={`Aumentar raio para ${maior} km`} onPress={() => onMudarRaio(maior)} /> : null}
        </EmptyState>
      }
      ListFooterComponent={<Fontes fontes={dados.fontes} />}
    />
  );
}

function Fontes({ fontes }: { fontes: Fonte[] }) {
  return (
    <View className="mx-4 mt-2 border-t border-slate-200 pt-3">
      <Text className="mb-1 text-xs font-semibold text-slate-600">Fontes</Text>
      {fontes.map((f) => (
        <Text
          key={f.nome}
          className={`text-xs ${f.url ? 'text-marca underline' : 'text-slate-500'}`}
          onPress={f.url ? () => void Linking.openURL(f.url ?? '') : undefined}
        >
          {f.nome} · atualizado na fonte: {formatarData(f.atualizado_na_fonte)} · importado em{' '}
          {formatarData(f.importado_em)}
        </Text>
      ))}
      <Text className="mt-2 text-xs text-slate-400">
        Localização aproximada: centro do município de cada estabelecimento.
      </Text>
    </View>
  );
}

function SkeletonDetalhe() {
  return (
    <View testID="skeleton-detalhe" accessibilityLabel="Carregando">
      <View className="border-b border-slate-200 bg-white p-4">
        <Skeleton className="mb-2 h-6 w-3/4" />
        <Skeleton className="mb-1 h-4 w-1/2" />
        <Skeleton className="mb-4 h-4 w-2/3" />
        <Skeleton className="h-20 w-full" />
      </View>
      {[0, 1, 2].map((i) => (
        <View key={i} className="mx-4 mt-3 rounded-xl border border-slate-200 bg-white p-4">
          <Skeleton className="mb-2 h-5 w-2/3" />
          <Skeleton className="mb-3 h-4 w-1/2" />
          <Skeleton className="h-4 w-full" />
        </View>
      ))}
    </View>
  );
}
