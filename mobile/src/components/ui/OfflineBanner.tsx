import { Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

/** Aviso fixo no rodapé enquanto o aparelho está sem conexão. */
export function OfflineBanner() {
  const { online } = useNetworkStatus();
  const { bottom } = useSafeAreaInsets();
  if (online) return null;
  return (
    <View
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      className="absolute inset-x-0 bottom-0 bg-slate-800 px-4 pt-2.5"
      style={{ paddingBottom: bottom + 10 }}
    >
      <Text className="text-center text-sm font-semibold text-white">Você está offline</Text>
      <Text className="text-center text-xs text-slate-300">Mostrando os últimos dados salvos no aparelho</Text>
    </View>
  );
}
