/** Substitui o react-native-maps nos testes: renderiza Views e dispara onMapReady. */
import { forwardRef, type ReactNode, useEffect, useImperativeHandle } from 'react';
import { View } from 'react-native';

interface PropsMapa {
  children?: ReactNode;
  onMapReady?: () => void;
  testID?: string;
}

const MapView = forwardRef<object, PropsMapa>(function MapView({ children, onMapReady, testID }, ref) {
  useImperativeHandle(ref, () => ({ fitToCoordinates: jest.fn(), animateToRegion: jest.fn() }));
  useEffect(() => onMapReady?.(), [onMapReady]);
  return <View testID={testID}>{children}</View>;
});

interface PropsMarcador {
  children?: ReactNode;
  onPress?: () => void;
  title?: string;
}

export function Marker({ children, onPress, title }: PropsMarcador) {
  return (
    <View testID="marcador" accessibilityLabel={title} onTouchEnd={onPress}>
      {children}
    </View>
  );
}

export function Polyline() {
  return <View testID="linha" />;
}

export default MapView;
