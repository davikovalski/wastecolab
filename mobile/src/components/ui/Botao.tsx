import { ActivityIndicator, Pressable, Text } from 'react-native';

type Variante = 'primario' | 'secundario' | 'texto';

interface Props {
  titulo: string;
  onPress: () => void;
  variante?: Variante;
  desabilitado?: boolean;
  carregando?: boolean;
  className?: string;
}

const FUNDO: Record<Variante, string> = {
  primario: 'bg-marca',
  secundario: 'bg-white border border-marca',
  texto: 'bg-transparent',
};
const TEXTO: Record<Variante, string> = {
  primario: 'text-white',
  secundario: 'text-marca',
  texto: 'text-marca',
};

export function Botao({ titulo, onPress, variante = 'primario', desabilitado, carregando, className = '' }: Props) {
  const inativo = desabilitado === true || carregando === true;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inativo, busy: carregando === true }}
      disabled={inativo}
      onPress={onPress}
      className={`min-h-11 flex-row items-center justify-center rounded-lg px-4 py-2.5 ${FUNDO[variante]} ${
        inativo ? 'opacity-50' : 'active:opacity-80'
      } ${className}`}
    >
      {carregando ? (
        <ActivityIndicator color={variante === 'primario' ? '#fff' : '#0F766E'} />
      ) : (
        <Text className={`text-base font-semibold ${TEXTO[variante]}`}>{titulo}</Text>
      )}
    </Pressable>
  );
}
