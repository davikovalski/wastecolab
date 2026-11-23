import * as Location from 'expo-location';
import { useCallback, useState } from 'react';

export type EstadoLocalizacao = 'ocioso' | 'buscando' | 'negado' | 'erro';

export interface Coordenada {
  lat: number;
  lon: number;
}

/** GPS sob demanda. Se a permissão for negada, não pergunta de novo: a tela oferece UF/município. */
export function useLocalizacao() {
  const [estado, setEstado] = useState<EstadoLocalizacao>('ocioso');

  const obter = useCallback(async (): Promise<Coordenada | null> => {
    setEstado('buscando');
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== Location.PermissionStatus.GRANTED) {
        setEstado('negado');
        return null;
      }
      const posicao = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setEstado('ocioso');
      return { lat: posicao.coords.latitude, lon: posicao.coords.longitude };
    } catch {
      setEstado('erro');
      return null;
    }
  }, []);

  return { estado, obter };
}
