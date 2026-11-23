import { useEffect, useState } from 'react';
import { Animated, View } from 'react-native';

/** Bloco cinza pulsante usado nos estados de carregamento. */
export function Skeleton({ className = '' }: { className?: string }) {
  const [opacidade] = useState(() => new Animated.Value(0.5));
  useEffect(() => {
    const animacao = Animated.loop(
      Animated.sequence([
        Animated.timing(opacidade, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(opacidade, { toValue: 0.5, duration: 700, useNativeDriver: true }),
      ]),
    );
    animacao.start();
    return () => animacao.stop();
  }, [opacidade]);
  return (
    <Animated.View style={{ opacity: opacidade }}>
      <View className={`rounded-md bg-slate-200 ${className}`} />
    </Animated.View>
  );
}

export function SkeletonCartao() {
  return (
    <View className="mx-4 mb-3 rounded-xl border border-slate-200 bg-white p-4">
      <Skeleton className="mb-2 h-5 w-3/4" />
      <Skeleton className="mb-4 h-4 w-1/3" />
      <Skeleton className="mb-2 h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </View>
  );
}

export function SkeletonLista({ quantidade = 6 }: { quantidade?: number }) {
  return (
    <View accessibilityLabel="Carregando" testID="skeleton-lista" className="pt-3">
      {Array.from({ length: quantidade }, (_, i) => (
        <SkeletonCartao key={i} />
      ))}
    </View>
  );
}
