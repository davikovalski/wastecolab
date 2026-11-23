import { useState } from 'react';
import { Modal, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Botao } from '@/components/ui/Botao';
import { Chip } from '@/components/ui/Chip';
import { useLocalizacao } from '@/hooks/useLocalizacao';
import { RAIOS_KM, UFS } from '@/lib/constantes';

import { BuscaMunicipio } from './BuscaMunicipio';
import { BuscaResiduo } from './BuscaResiduo';
import { descreverLocalizacao, ehUf, type Filtros, FILTROS_PADRAO } from './filtros';

interface Props {
  visivel: boolean;
  filtros: Filtros;
  onFechar: () => void;
  onAplicar: (filtros: Filtros) => void;
}

/**
 * Filtros da HU1. Edita um rascunho; a URL só muda ao tocar em "Aplicar".
 * Montado só enquanto aberto, então o rascunho sempre começa dos filtros atuais.
 */
export function PainelFiltros({ visivel, filtros, onFechar, onAplicar }: Props) {
  const [rascunho, setRascunho] = useState(filtros);
  const { estado: estadoGps, obter } = useLocalizacao();
  const { bottom } = useSafeAreaInsets();

  const atualizar = (parcial: Partial<Filtros>) => setRascunho((r) => ({ ...r, ...parcial }));
  const l = rascunho.localizacao;
  const ufAtual = l.tipo === 'uf' || l.tipo === 'municipio' ? l.uf : null;

  const usarGps = async () => {
    const coordenada = await obter();
    if (coordenada) atualizar({ localizacao: { tipo: 'gps', ...coordenada } });
  };

  return (
    <Modal visible={visivel} animationType="slide" presentationStyle="pageSheet" onRequestClose={onFechar}>
      <View className="flex-1 bg-slate-50">
        <View className="flex-row items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
          <Text className="text-lg font-semibold text-slate-900">Filtros</Text>
          <Botao titulo="Fechar" variante="texto" onPress={onFechar} />
        </View>

        <ScrollView className="flex-1" contentContainerClassName="p-4 pb-8" keyboardShouldPersistTaps="handled">
          <Secao titulo="Localização" detalhe={descreverLocalizacao(l)}>
            <Botao
              titulo={l.tipo === 'gps' ? 'Atualizar minha localização' : 'Usar minha localização'}
              variante="secundario"
              carregando={estadoGps === 'buscando'}
              onPress={() => void usarGps()}
            />
            {estadoGps === 'negado' ? (
              <Text className="mt-2 text-sm text-aterro">
                Sem permissão de localização. Escolha a UF e o município abaixo.
              </Text>
            ) : null}
            {estadoGps === 'erro' ? (
              <Text className="mt-2 text-sm text-aterro">
                Não foi possível obter sua localização. Escolha a UF e o município abaixo.
              </Text>
            ) : null}

            <Text className="mb-2 mt-4 text-sm font-medium text-slate-700">UF</Text>
            <View className="flex-row flex-wrap">
              <Chip
                rotulo="Todas"
                selecionado={l.tipo === 'brasil'}
                onPress={() => atualizar({ localizacao: { tipo: 'brasil' } })}
              />
              {UFS.map((uf) => (
                <Chip
                  key={uf}
                  rotulo={uf}
                  selecionado={ufAtual === uf}
                  onPress={() => atualizar({ localizacao: { tipo: 'uf', uf } })}
                />
              ))}
            </View>

            <Text className="mb-2 mt-2 text-sm font-medium text-slate-700">Município</Text>
            {l.tipo === 'municipio' ? (
              <Chip
                rotulo={`${l.nome}/${l.uf}  ✕`}
                selecionado
                onPress={() => atualizar({ localizacao: { tipo: 'uf', uf: l.uf } })}
              />
            ) : (
              <BuscaMunicipio
                uf={ufAtual}
                onSelecionar={(m) => {
                  if (ehUf(m.uf))
                    atualizar({ localizacao: { tipo: 'municipio', id: m.id_ibge, nome: m.nome, uf: m.uf } });
                }}
              />
            )}
          </Secao>

          <Secao titulo="Resíduo">
            <BuscaResiduo
              selecionado={rascunho.residuo}
              perigoso={rascunho.perigoso}
              onSelecionar={(residuo) => atualizar({ residuo })}
            />
          </Secao>

          <Secao titulo="Classe">
            <View className="flex-row flex-wrap">
              <Chip
                rotulo="Todos"
                selecionado={rascunho.perigoso === null}
                onPress={() => atualizar({ perigoso: null })}
              />
              <Chip
                rotulo="Perigosos"
                selecionado={rascunho.perigoso === true}
                onPress={() => atualizar({ perigoso: true })}
              />
              <Chip
                rotulo="Não perigosos"
                selecionado={rascunho.perigoso === false}
                onPress={() => atualizar({ perigoso: false })}
              />
            </View>
          </Secao>

          <Secao titulo="Raio até o destinador">
            <View className="flex-row flex-wrap">
              {RAIOS_KM.map((raio) => (
                <Chip
                  key={raio}
                  rotulo={`${raio} km`}
                  selecionado={rascunho.raioKm === raio}
                  onPress={() => atualizar({ raioKm: raio })}
                />
              ))}
            </View>
          </Secao>

          <Secao titulo="Ordenar por">
            <View className="flex-row flex-wrap">
              <Chip
                rotulo="Maior quantidade"
                selecionado={rascunho.ordem === 'quantidade'}
                onPress={() => atualizar({ ordem: 'quantidade' })}
              />
              <Chip
                rotulo="Destinador mais perto"
                selecionado={rascunho.ordem === 'distancia'}
                onPress={() => atualizar({ ordem: 'distancia' })}
              />
            </View>
          </Secao>
        </ScrollView>

        <View
          className="flex-row gap-3 border-t border-slate-200 bg-white px-4 pt-3"
          style={{ paddingBottom: bottom + 12 }}
        >
          <Botao titulo="Limpar" variante="secundario" className="flex-1" onPress={() => setRascunho(FILTROS_PADRAO)} />
          <Botao titulo="Aplicar" className="flex-1" onPress={() => onAplicar(rascunho)} />
        </View>
      </View>
    </Modal>
  );
}

function Secao({ titulo, detalhe, children }: { titulo: string; detalhe?: string; children: React.ReactNode }) {
  return (
    <View className="mb-6">
      <View className="mb-2 flex-row items-baseline justify-between">
        <Text className="text-base font-semibold text-slate-900">{titulo}</Text>
        {detalhe ? <Text className="text-sm text-slate-500">{detalhe}</Text> : null}
      </View>
      {children}
    </View>
  );
}
