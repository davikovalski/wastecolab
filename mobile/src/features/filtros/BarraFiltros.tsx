import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { formatarCodigoResiduo } from '@/lib/formatar';

import { descreverLocalizacao, type Filtros } from './filtros';
import { PainelFiltros } from './PainelFiltros';
import { useFiltros, type Visao } from './useFiltros';

/** Topo da lista e do mapa: resumo dos filtros, botão de filtros e alternância Lista/Mapa. */
export function BarraFiltros({ visao }: { visao: Visao }) {
  const { filtros, aplicar, irPara } = useFiltros();
  const [aberto, setAberto] = useState(false);

  return (
    <View className="border-b border-slate-200 bg-white px-4 pb-3 pt-2">
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Abrir filtros"
        onPress={() => setAberto(true)}
        className="rounded-lg bg-slate-100 px-3 py-2.5 active:bg-slate-200"
      >
        <Text className="text-sm text-slate-800" numberOfLines={1}>
          {resumo(filtros)}
        </Text>
        <Text className="text-xs font-semibold text-marca">Alterar filtros</Text>
      </Pressable>

      <View className="mt-2 flex-row rounded-lg bg-slate-100 p-1" accessibilityRole="tablist">
        <Aba rotulo="Lista" ativa={visao === 'lista'} onPress={() => irPara('lista')} />
        <Aba rotulo="Mapa" ativa={visao === 'mapa'} onPress={() => irPara('mapa')} />
      </View>

      {aberto ? (
        <PainelFiltros
          visivel
          filtros={filtros}
          onFechar={() => setAberto(false)}
          onAplicar={(novos) => {
            aplicar(novos);
            setAberto(false);
          }}
        />
      ) : null}
    </View>
  );
}

function resumo(f: Filtros): string {
  const partes = [descreverLocalizacao(f.localizacao), `até ${f.raioKm} km`];
  if (f.residuo) partes.push(formatarCodigoResiduo(f.residuo.codigo));
  if (f.perigoso !== null) partes.push(f.perigoso ? 'perigosos' : 'não perigosos');
  return partes.join(' · ');
}

function Aba({ rotulo, ativa, onPress }: { rotulo: string; ativa: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="tab"
      accessibilityState={{ selected: ativa }}
      onPress={ativa ? undefined : onPress}
      className={`flex-1 items-center rounded-md py-1.5 ${ativa ? 'bg-white shadow-sm' : ''}`}
    >
      <Text className={`text-sm ${ativa ? 'font-semibold text-marca' : 'text-slate-600'}`}>{rotulo}</Text>
    </Pressable>
  );
}
