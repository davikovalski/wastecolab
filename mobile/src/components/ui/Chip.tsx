import { Pressable, Text } from 'react-native';

interface Props {
  rotulo: string;
  selecionado?: boolean;
  onPress: () => void;
}

export function Chip({ rotulo, selecionado = false, onPress }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: selecionado }}
      onPress={onPress}
      className={`mb-2 mr-2 rounded-full border px-3.5 py-2 ${
        selecionado ? 'border-marca bg-marca' : 'border-slate-300 bg-white active:bg-slate-100'
      }`}
    >
      <Text className={`text-sm ${selecionado ? 'font-semibold text-white' : 'text-slate-700'}`}>{rotulo}</Text>
    </Pressable>
  );
}
