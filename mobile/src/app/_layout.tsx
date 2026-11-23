import '../../global.css';

import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { View } from 'react-native';

import { OfflineBanner } from '@/components/ui/OfflineBanner';
import { conectarStatusDeRede } from '@/hooks/useNetworkStatus';
import { criarQueryClient, OPCOES_PERSISTENCIA } from '@/lib/queryClient';

conectarStatusDeRede();

export default function Layout() {
  const [queryClient] = useState(criarQueryClient);
  return (
    <PersistQueryClientProvider client={queryClient} persistOptions={OPCOES_PERSISTENCIA}>
      <View className="flex-1 bg-slate-50">
        <Stack
          screenOptions={{
            headerTintColor: '#0F766E',
            headerTitleStyle: { color: '#0F172A' },
            contentStyle: { backgroundColor: '#F8FAFC' },
          }}
        >
          <Stack.Screen name="index" options={{ title: 'Oportunidades', animation: 'none' }} />
          <Stack.Screen name="mapa" options={{ title: 'Mapa', animation: 'none' }} />
          <Stack.Screen name="oportunidade/[cnpj]/[codigo]" options={{ title: 'Oportunidade' }} />
        </Stack>
        <OfflineBanner />
        <StatusBar style="dark" />
      </View>
    </PersistQueryClientProvider>
  );
}
