import { Link } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';

import type { OportunidadeItem } from '@/api/tipos';
import { Botao } from '@/components/ui/Botao';
import { EstadoConsulta } from '@/components/ui/EstadoConsulta';
import { useDetalhe } from '@/features/detalhe/useDetalhe';
import type { Filtros } from '@/features/filtros/filtros';
import { useFiltros } from '@/features/filtros/useFiltros';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import type { RaioKm } from '@/lib/constantes';
import { formatarCodigoResiduo, formatarKm, formatarQuantidade, pluralizar } from '@/lib/formatar';

import {
  agruparPorMunicipio,
  bboxDaRegiao,
  criarIndice,
  type PontoMunicipio,
  REGIAO_BRASIL,
  type Regiao,
  regiaoComZoom,
  tamanhoMarcador,
  zoomDaRegiao,
} from './agrupamento';
import { rotaDetalhe } from './CartaoOportunidade';
import { SemResultados } from './SemResultados';
import { useOportunidades } from './useOportunidades';

const COR_MARCA = '#0F766E';
/** Se o mapa não ficar pronto nesse tempo (ex.: sem tiles offline), oferecemos a lista. */
const ESPERA_MAPA_MS = 10_000;

/** HU2: mesmos filtros e mesma consulta da lista, agrupados por município. */
export function MapaOportunidades() {
  const { filtros, irPara } = useFiltros();
  const consulta = useOportunidades(filtros);

  return (
    <EstadoConsulta
      consulta={consulta}
      carregando={
        <View className="flex-1 items-center justify-center bg-slate-100" testID="mapa-carregando">
          <ActivityIndicator size="large" color={COR_MARCA} />
          <Text className="mt-3 text-sm text-slate-600">Buscando oportunidades…</Text>
        </View>
      }
    >
      {consulta.itens.length === 0 ? (
        <SemResultados />
      ) : (
        <Mapa
          filtros={filtros}
          itens={consulta.itens}
          total={consulta.total}
          carregarMais={consulta.hasNextPage ? () => void consulta.fetchNextPage() : null}
          carregandoMais={consulta.isFetchingNextPage}
          verLista={() => irPara('lista')}
        />
      )}
    </EstadoConsulta>
  );
}

interface PropsMapa {
  filtros: Filtros;
  itens: OportunidadeItem[];
  total: number;
  carregarMais: (() => void) | null;
  carregandoMais: boolean;
  verLista: () => void;
}

function regiaoInicial(f: Filtros): Regiao {
  return f.localizacao.tipo === 'gps' ? regiaoComZoom(f.localizacao.lat, f.localizacao.lon, 8) : REGIAO_BRASIL;
}

function Mapa({ filtros, itens, total, carregarMais, carregandoMais, verLista }: PropsMapa) {
  const mapa = useRef<MapView>(null);
  const { online } = useNetworkStatus();
  const [regiao, setRegiao] = useState<Regiao>(() => regiaoInicial(filtros));
  const [pronto, setPronto] = useState(false);
  const [demorou, setDemorou] = useState(false);
  const [municipio, setMunicipio] = useState<PontoMunicipio | null>(null);
  const [selecionado, setSelecionado] = useState<OportunidadeItem | null>(null);

  const pontos = useMemo(() => agruparPorMunicipio(itens), [itens]);
  const indice = useMemo(() => criarIndice(pontos), [pontos]);
  const marcadores = useMemo(() => indice.marcadores(bboxDaRegiao(regiao), zoomDaRegiao(regiao)), [indice, regiao]);

  useEffect(() => {
    if (pronto) return;
    const t = setTimeout(() => setDemorou(true), ESPERA_MAPA_MS);
    return () => clearTimeout(t);
  }, [pronto]);

  // Enquadra os pontos quando o mapa fica pronto e quando os filtros mudam.
  useEffect(() => {
    if (!pronto || pontos.length === 0) return;
    mapa.current?.fitToCoordinates(
      pontos.map((p) => ({ latitude: p.lat, longitude: p.lon })),
      { edgePadding: { top: 80, right: 60, bottom: 220, left: 60 }, animated: true },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pronto, filtros]);

  const abrirMunicipio = (ponto: PontoMunicipio) => {
    setMunicipio(ponto);
    setSelecionado(ponto.itens[0] ?? null);
  };

  return (
    <View className="flex-1">
      <MapView
        ref={mapa}
        style={{ flex: 1 }}
        initialRegion={regiao}
        onMapReady={() => setPronto(true)}
        onRegionChangeComplete={(r: Regiao) => setRegiao(r)}
        toolbarEnabled={false}
        testID="mapa"
      >
        {marcadores.map((m) =>
          m.tipo === 'grupo' ? (
            <Marker
              key={`g${m.id}`}
              coordinate={{ latitude: m.lat, longitude: m.lon }}
              tracksViewChanges={false}
              onPress={() =>
                mapa.current?.animateToRegion(regiaoComZoom(m.lat, m.lon, indice.zoomParaAbrir(m.id)), 400)
              }
            >
              <Bolha toneladas={m.toneladas} rotulo={String(m.geradores)} />
            </Marker>
          ) : (
            <Marker
              key={`m${m.ponto.chave}`}
              coordinate={{ latitude: m.ponto.lat, longitude: m.ponto.lon }}
              tracksViewChanges={false}
              onPress={() => abrirMunicipio(m.ponto)}
            >
              <Bolha
                toneladas={m.ponto.toneladas}
                rotulo={String(m.ponto.itens.length)}
                destaque={municipio?.chave === m.ponto.chave}
              />
            </Marker>
          ),
        )}
        {selecionado ? <RotasNoMapa item={selecionado} raioKm={filtros.raioKm} /> : null}
      </MapView>

      <View className="absolute inset-x-3 top-3 gap-2" pointerEvents="box-none">
        <View className="rounded-lg bg-white/95 px-3 py-2 shadow-sm">
          <Text className="text-xs text-slate-700">Localização aproximada (centro do município)</Text>
        </View>
        {!online || (demorou && !pronto) ? (
          <View className="rounded-lg bg-amber-50 px-3 py-2 shadow-sm" testID="aviso-mapa">
            <Text className="mb-2 text-xs text-amber-900">
              {online ? 'O mapa está demorando para carregar.' : 'Sem conexão: o mapa pode não carregar.'}
            </Text>
            <Botao titulo="Ver em lista" variante="secundario" onPress={verLista} />
          </View>
        ) : null}
        {itens.length < total ? (
          <View className="flex-row items-center justify-between rounded-lg bg-white/95 px-3 py-1.5 shadow-sm">
            <Text className="text-xs text-slate-700">
              Mostrando {itens.length} de {total}
            </Text>
            {carregarMais ? (
              <Botao titulo="Carregar mais" variante="texto" carregando={carregandoMais} onPress={carregarMais} />
            ) : null}
          </View>
        ) : null}
      </View>

      {municipio ? (
        <CartaoMunicipio
          ponto={municipio}
          selecionado={selecionado}
          raioKm={filtros.raioKm}
          onSelecionar={setSelecionado}
          onFechar={() => {
            setMunicipio(null);
            setSelecionado(null);
          }}
        />
      ) : null}
    </View>
  );
}

function Bolha({ toneladas, rotulo, destaque = false }: { toneladas: number; rotulo: string; destaque?: boolean }) {
  const d = tamanhoMarcador(toneladas);
  return (
    <View
      style={{ width: d, height: d, borderRadius: d / 2 }}
      className={`items-center justify-center border-2 border-white ${destaque ? 'bg-aterro' : 'bg-marca'}`}
    >
      <Text className="text-xs font-bold text-white">{rotulo}</Text>
    </View>
  );
}

/** Linhas do gerador até cada destinador candidato (HU2, critério 3). */
function RotasNoMapa({ item, raioKm }: { item: OportunidadeItem; raioKm: RaioKm }) {
  const { data } = useDetalhe({ cnpj: item.gerador.cnpj, codigo: item.residuo.codigo, raioKm });
  if (!data) return null;
  const origem = { latitude: item.localizacao.lat, longitude: item.localizacao.lon };
  return (
    <>
      {data.rotas.map((rota) => {
        const destino = { latitude: rota.localizacao.lat, longitude: rota.localizacao.lon };
        return [
          <Polyline
            key={`l${rota.destinador.cnpj}`}
            coordinates={[origem, destino]}
            strokeColor={COR_MARCA}
            strokeWidth={2}
          />,
          <Marker
            key={`d${rota.destinador.cnpj}`}
            coordinate={destino}
            pinColor="green"
            title={rota.destinador.razao_social}
            description={formatarKm(rota.distancia_km)}
          />,
        ];
      })}
    </>
  );
}

interface PropsCartao {
  ponto: PontoMunicipio;
  selecionado: OportunidadeItem | null;
  raioKm: RaioKm;
  onSelecionar: (item: OportunidadeItem) => void;
  onFechar: () => void;
}

function CartaoMunicipio({ ponto, selecionado, raioKm, onSelecionar, onFechar }: PropsCartao) {
  const detalhe = useDetalhe(
    selecionado ? { cnpj: selecionado.gerador.cnpj, codigo: selecionado.residuo.codigo, raioKm } : null,
  );
  return (
    <View className="absolute inset-x-3 bottom-3 rounded-xl bg-white p-3 shadow-lg" testID="cartao-municipio">
      <View className="mb-2 flex-row items-center justify-between">
        <Text className="flex-1 text-base font-semibold text-slate-900">
          {ponto.nome} · {pluralizar(ponto.itens.length, 'oportunidade', 'oportunidades')}
        </Text>
        <Pressable accessibilityRole="button" accessibilityLabel="Fechar" onPress={onFechar} hitSlop={12}>
          <Text className="px-1 text-lg text-slate-500">✕</Text>
        </Pressable>
      </View>

      {ponto.itens.length > 1 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-2">
          {ponto.itens.map((item) => {
            const ativo = item === selecionado;
            return (
              <Pressable
                key={`${item.gerador.cnpj}-${item.residuo.codigo}`}
                accessibilityRole="button"
                accessibilityState={{ selected: ativo }}
                onPress={() => onSelecionar(item)}
                className={`mr-2 max-w-48 rounded-lg border px-2.5 py-1.5 ${ativo ? 'border-marca bg-marca-claro' : 'border-slate-200'}`}
              >
                <Text className="text-xs font-semibold text-slate-800" numberOfLines={1}>
                  {item.gerador.razao_social}
                </Text>
                <Text className="text-xs text-slate-500">{formatarCodigoResiduo(item.residuo.codigo)}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}

      {selecionado ? (
        <View>
          <Text className="text-sm font-semibold text-slate-900" numberOfLines={1}>
            {selecionado.gerador.razao_social}
          </Text>
          <Text className="text-xs text-slate-600" numberOfLines={1}>
            {formatarCodigoResiduo(selecionado.residuo.codigo)} · {selecionado.residuo.descricao} ·{' '}
            {formatarQuantidade(selecionado.quantidade)}
          </Text>
          <Text className="mb-2 mt-1 text-xs text-marca-escuro">
            {detalhe.isPending && detalhe.fetchStatus === 'fetching'
              ? 'Carregando destinadores…'
              : detalhe.isError && !detalhe.data
                ? 'Não deu para carregar as linhas dos destinadores.'
                : `${pluralizar(selecionado.rotas.total, 'destinador', 'destinadores')} em até ${raioKm} km · mais próximo a ${formatarKm(selecionado.rotas.distancia_mais_proxima_km)}`}
          </Text>
          <Link href={rotaDetalhe(selecionado, raioKm)} asChild>
            <Pressable accessibilityRole="button" className="items-center rounded-lg bg-marca py-2.5 active:opacity-80">
              <Text className="text-sm font-semibold text-white">Ver detalhe</Text>
            </Pressable>
          </Link>
        </View>
      ) : null}
    </View>
  );
}
