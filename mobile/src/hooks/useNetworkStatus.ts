import NetInfo from '@react-native-community/netinfo';
import { onlineManager } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';

/**
 * Liga o NetInfo ao onlineManager do TanStack Query: offline, as consultas pausam e o app
 * continua mostrando o cache. Chamar uma vez, no layout raiz.
 */
export function conectarStatusDeRede(): void {
  onlineManager.setEventListener((setOnline) =>
    NetInfo.addEventListener((estado) => {
      // `isInternetReachable` é null enquanto o aparelho ainda não testou: não conta como offline.
      setOnline(estado.isConnected !== false && estado.isInternetReachable !== false);
    }),
  );
}

const assinar = (aviso: () => void) => onlineManager.subscribe(aviso);
const ler = () => onlineManager.isOnline();

export function useNetworkStatus(): { online: boolean } {
  return { online: useSyncExternalStore(assinar, ler, ler) };
}
