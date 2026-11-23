import { Text, View } from 'react-native';

import { mensagemDoErro } from '@/api/erros';

import { Botao } from './Botao';

interface Props {
  erro: unknown;
  onTentarNovamente: () => void;
  tentando?: boolean;
  /** Texto no lugar da mensagem padrão do código de erro. */
  mensagem?: string;
}

export function ErrorState({ erro, onTentarNovamente, tentando, mensagem }: Props) {
  return (
    <View className="flex-1 items-center justify-center px-8 py-12" testID="estado-erro">
      <Text className="mb-2 text-center text-lg font-semibold text-slate-800">Não deu para carregar</Text>
      <Text className="mb-6 text-center text-base text-slate-600">{mensagem ?? mensagemDoErro(erro)}</Text>
      <Botao titulo="Tentar novamente" onPress={onTentarNovamente} carregando={tentando} className="w-full" />
    </View>
  );
}
