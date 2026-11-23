import { Text, View } from 'react-native';

import type { Oportunidade } from '@/api/tipos';
import {
  formatarCnpj,
  formatarCodigoResiduo,
  formatarPerigoso,
  formatarQuantidadeCompleta,
  formatarTexto,
  NAO_INFORMADO,
} from '@/lib/formatar';

/** Gerador e resíduo (HU3, critério 1). */
export function CabecalhoOportunidade({ oportunidade }: { oportunidade: Oportunidade }) {
  const { gerador, residuo } = oportunidade;
  const municipio = gerador.municipio ? `${gerador.municipio.nome}/${gerador.municipio.uf}` : NAO_INFORMADO;
  const atividade = [gerador.categoria_atividade, gerador.detalhe_atividade].filter(Boolean).join(' – ');

  return (
    <View className="border-b border-slate-200 bg-white p-4">
      <Text className="text-lg font-bold text-slate-900">{gerador.razao_social}</Text>
      <Linha rotulo="CNPJ" valor={formatarCnpj(gerador.cnpj)} />
      <Linha rotulo="Atividade" valor={formatarTexto(atividade)} />
      <Linha rotulo="Município" valor={municipio} />

      <View className="mt-4 rounded-lg bg-slate-50 p-3">
        <Text className="text-sm font-semibold text-slate-900">
          {formatarCodigoResiduo(residuo.codigo)} · {residuo.descricao}
        </Text>
        <Linha rotulo="Classe" valor={formatarPerigoso(residuo.perigoso)} />
        <Linha
          rotulo={`Quantidade em ${oportunidade.ano}`}
          valor={formatarQuantidadeCompleta(oportunidade.quantidade)}
        />
        <Text className="mt-1 text-sm text-aterro">
          Hoje vai para:{' '}
          {oportunidade.operacoes_atuais.length > 0
            ? oportunidade.operacoes_atuais.map((o) => `${o.codigo} – ${o.descricao}`).join(' · ')
            : NAO_INFORMADO}
        </Text>
      </View>
    </View>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <Text className="mt-1 text-sm text-slate-700">
      <Text className="text-slate-500">{rotulo}: </Text>
      {valor}
    </Text>
  );
}
