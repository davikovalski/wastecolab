# Waste Colab — Etapa 4: Arquitetura do app (proposta)

> Status: **aprovada pelo Davi em 23/11/2026 e implementada** (pasta `mobile/`). Ajustes feitos na implementação estão na seção 8.

## 1. Visão geral

```
 Telas (Expo Router)        Estado de servidor             Rede
 ───────────────────        ──────────────────             ────
 index      (HU1 lista)  ┐                                 
 mapa       (HU2)        ├─► hooks de feature ─► TanStack Query ─► cliente tipado ─► API FastAPI /v1
 oportunidade/[cnpj]/    ┘      (useOportunidades,         (cache + retry +        (openapi-fetch +
   [codigo] (HU3)                useDetalhe…)               persistência offline)   tipos gerados do OpenAPI)
        ▲                                                   ▲
        └── filtros na URL (search params)                  └── NetInfo → onlineManager (sabe quando está offline)
```

São três ideias centrais:
1. **Os filtros ficam na URL** (search params do Expo Router). Lista e mapa leem os mesmos parâmetros, então alternar entre eles mantém os filtros e reaproveita a mesma consulta em cache, sem buscar de novo (critério 1 da HU2).
2. **Todo dado vem do TanStack Query**, persistido no aparelho (AsyncStorage). Offline, o app mostra o último resultado com a data, e o banner "Você está offline" (critérios 7 da HU1 e 6 da HU3).
3. **Tipos gerados da API.** O `openapi-typescript` lê o `/openapi.json` da FastAPI e gera `src/api/schema.d.ts`. O `openapi-fetch` usa esses tipos, então URL, parâmetros e respostas são checados pelo TypeScript. Não há `any` em lugar nenhum: o ESLint trata `no-explicit-any` como erro.

## 2. Telas e estados

| Tela | Rota | Loading | Vazio | Erro / offline |
|---|---|---|---|---|
| **Lista** (HU1) | `/` | Skeleton de 6 cartões | "Nenhuma oportunidade" + **Aumentar raio** e **Limpar filtros** | Banner offline + último resultado com data; sem cache: ErrorState com **Tentar novamente** |
| **Mapa** (HU2) | `/mapa` | Spinner sobre o mapa | Mesmo EmptyState da lista | Igual à lista. Se os tiles não carregarem, aviso + **Ver em lista** |
| **Detalhe** (HU3) | `/oportunidade/[cnpj]/[codigo]` | Skeleton do cabeçalho e das rotas | "Nenhum destinador no raio" + **Aumentar raio** | Abre do cache se já foi visto; senão ErrorState |
| **Filtros** | `/filtros` (modal) | Busca de resíduo e município com debounce | "Nada encontrado" | Mensagem curta + tentar de novo |

**Filtros (HU1):** localização (GPS ou UF/município), resíduo (busca por código ou descrição), perigoso (sim/não/todos), raio (chips 25, 50, 100, 250 e 500 km) e ordem (quantidade ou distância).

**GPS:** usa `expo-location`. Se a permissão for negada, o app não insiste: abre direto a escolha de UF/município.

**Lista:** `FlashList` com rolagem infinita (`useInfiniteQuery`, 20 por página, usando `total` da API).

**Mapa:** `react-native-maps` com agrupamento de marcadores (`supercluster`). O tamanho do marcador indica a quantidade, e há um aviso fixo de "Localização aproximada (centro do município)". Ao tocar num gerador, o detalhe é buscado e as linhas até os destinadores são desenhadas.

**Detalhe:** mostra os dados do gerador, com o CNPJ formatado. Cada rota aparece num cartão com a distância, as operações R, a quantidade recebida e um resumo do município (coleta seletiva, plano com link, metas) ou "Município sem diagnóstico". No rodapé ficam as fontes e as datas.

## 3. Tratamento de erros e rede

- `src/api/erros.ts` define `ErroApi` (com o `codigo` do formato único da API) e `ErroRede` (falha de conexão ou timeout de 15 s).
- O TanStack Query tenta de novo até 2 vezes, mas só em `ErroRede` e `banco_indisponivel`. Nunca repete em 404 ou 422.
- Componentes compartilhados: `Skeleton`, `EmptyState`, `ErrorState` (mensagem por `codigo` + **Tentar novamente**), `OfflineBanner` e `DataAtualizacao` ("Dados de 23/11, 09:40").
- Campos `null` da API aparecem como **"Não informado"** por meio de um único formatador (`formatar.ts`), que também formata toneladas, litros, km e CNPJ.

## 4. Decisões técnicas (para aprovar)

1. **Expo SDK estável atual**, com Expo Router, TypeScript `strict` e NativeWind v4 (Tailwind).
2. **TanStack Query v5 + persistência em AsyncStorage**, com dados válidos por 5 minutos (igual ao `max-age` da API) e guardados por 7 dias para o modo offline.
3. **Filtros na URL**, sem biblioteca de estado global (sem Redux nem Zustand).
4. **openapi-typescript + openapi-fetch** para o cliente HTTP, em vez de escrever os tipos à mão.
5. **Mapa:** `react-native-maps` + `supercluster`. Funciona no Expo Go para testar. Para publicar no Android vai ser preciso uma chave do Google Maps, mas isso fica para a etapa de publicação.
6. **URL da API** em `EXPO_PUBLIC_API_URL`. Para testar no celular, é o IP do computador na rede local (ex.: `http://192.168.0.10:8000`).

## 5. Estrutura de pastas

```
mobile/
├── app.json · tailwind.config.js · babel.config.js · metro.config.js · global.css
├── tsconfig.json                    # strict + paths "@/*"
├── eslint.config.js                 # no-explicit-any = erro
├── app/
│   ├── _layout.tsx                  # QueryClient persistido, NetInfo, OfflineBanner, Stack
│   ├── index.tsx                    # HU1 lista
│   ├── mapa.tsx                     # HU2 mapa
│   ├── filtros.tsx                  # modal de filtros
│   └── oportunidade/[cnpj]/[codigo].tsx   # HU3 detalhe
└── src/
    ├── api/
    │   ├── schema.d.ts              # gerado (npm run gerar:api)
    │   ├── cliente.ts               # openapi-fetch + timeout + conversão de erros
    │   └── erros.ts
    ├── features/
    │   ├── filtros/                 # useFiltros (lê/escreve search params), ChipsRaio, BuscaResiduo…
    │   ├── oportunidades/           # useOportunidades (infinite), CartaoOportunidade, MapaOportunidades
    │   └── detalhe/                 # useDetalhe, CartaoRota, ContextoMunicipal
    ├── components/ui/               # Skeleton, EmptyState, ErrorState, OfflineBanner, DataAtualizacao, Chip
    ├── hooks/                       # useNetworkStatus, useLocalizacao
    └── lib/                         # formatar.ts, queryClient.ts, constantes.ts
```

## 6. Qualidade

- `tsc --noEmit`, ESLint e testes com Jest (`jest-expo` + Testing Library). Os testes cobrem:
  - os estados de loading, vazio e erro de cada tela, com a API simulada;
  - a conversão de erros do cliente;
  - os formatadores ("Não informado", CNPJ, t, km);
  - `useFiltros` (URL ↔ filtros).
- Daqui eu consigo rodar o typecheck, o lint, os testes e um build web de verificação. **Não consigo abrir o app num celular**: o teste no aparelho fica com você, via Expo Go (`npx expo start`), com a API rodando no seu computador.

## 7. Fora desta etapa

Login, favoritos, notificações, publicação nas lojas (EAS Build), chave do Google Maps de produção e deploy da API.

## 8. Notas da implementação

- **Expo SDK 58** (React Native 0.88, React 19.3, TypeScript 6). As telas ficam em `mobile/src/app/`, a convenção atual do Expo Router, em vez de `mobile/app/`.
- **Filtros num painel modal** dentro da lista e do mapa, em vez da rota `/filtros`. O painel edita um rascunho e grava na URL só ao tocar em "Aplicar", o que evita sincronizar duas rotas.
- **Mapa e paginação:** o mapa mostra as páginas já carregadas pela lista (mesma consulta) e tem "Carregar mais" quando há mais resultados. Os geradores são agrupados por município e, conforme o zoom, os municípios próximos viram grupos (`supercluster`).
- **Tiles do mapa:** sem conexão, ou se o mapa não ficar pronto em 10 s, aparece um aviso com "Ver em lista".
- **Contrato da API:** `backend/app/exportar_openapi.py` gera `mobile/openapi.json` sem precisar do banco; `npm run gerar:api` gera os tipos. Um teste do backend falha se o arquivo ficar desatualizado.
- **Web:** o build web serve só para verificação; no navegador o mapa mostra um aviso e o botão "Ver em lista".
