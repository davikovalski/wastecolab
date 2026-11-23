# Waste Colab — Etapa 1: Escopo do MVP, Banco de Dados e Arquitetura

> **v3 (23/11/2026).** Esta versão foi refeita depois de baixar e analisar os dados abertos do RAPP/IBAMA, a fonte escolhida pelo Davi. Decisões já confirmadas: as destinações de valorização, sem login no MVP, geolocalização pelo IBGE e uso da declaração mais recente de cada município. A rota como destinador do RAPP foi **confirmada pelo Davi**. Escopo aprovado.

## 0. O que os dados realmente contêm

### 0.1 IBAMA RAPP: Resíduos Sólidos – Destinador (a base principal)
Fonte: `dadosabertos.ibama.gov.br/dados/RAPP/residuoSolidosDestinador/relatorio.csv` (73 MB, atualizada em 04/05/2026, separador `;`, UTF-8, números no formato `53.980,00`).

| Item | Valor |
|---|---|
| Linhas | 170.400. Cada uma é uma movimentação: **gerador (CNPJ) → destinador (CNPJ)**, com código do resíduo, ano, quantidade e **operação de destinação** |
| Destinadores | 3.098 (2.263 fazem alguma operação de valorização, código R) |
| Geradores | 26.702 |
| Códigos de resíduo | 778, todos com 6 dígitos, da Lista Brasileira de Resíduos (ex.: `170107`) |
| Anos | 2011 a 2025. O mais frequente é 2024 (30 mil linhas) |
| Unidades | kg (89%), litros (9%), unidades (2%) |
| Situação cadastral | 94% "Ativa" |
| Localização | Só **Estado e Município do destinador**, em maiúsculas e sem acento. Não tem endereço nem coordenadas |

Operações de destinação (Anexo da Resolução CONAMA / Convenção de Basileia):
- **Aterro (D1, D4, D5):** 48.085 linhas. D5 "Aterramentos especialmente projetados" é a operação mais frequente da base, com 44.532 linhas.
- **Valorização (R1 a R12):** reciclagem de metais (R4), de inorgânicos (R5) e de orgânicos (R3), uso como combustível (R1), re-refino de óleo (R9), uso agrícola (R10) etc.
- **Outras eliminações (D2, D3, D8 a D14):** incineração, tratamento físico-químico, armazenamento etc.

**O dado que muda o produto:** existem **27.745 pares (gerador, código de resíduo) destinados a aterro, de 10.145 geradores**. Em **27.577 desses pares (99%), o mesmo código de resíduo é valorizado (operação R) por algum destinador da base.** Ou seja, a própria base do IBAMA já identifica a oportunidade e também a rota (um destinador real que já recebe aquele resíduo para valorizar).

### 0.2 IBAMA RAPP: Resíduos Sólidos – Gerador (a partir de 2012)
O arquivo tem 826 MB e 2,8 milhões de linhas, com 131.983 CNPJs. **Não informa a destinação**, só a geração. Serve para pegar o **município do gerador**, que não vem no arquivo do destinador. Cruzamento testado: 10.121 dos 10.145 geradores que destinam a aterro (99,8%) têm município nesse arquivo. O ETL lê o arquivo em *streaming* e guarda só CNPJ, razão social, município, UF e atividade.

### 0.3 Diagnóstico municipal (o CSV anexado)
São 1.013 declarações de 991 municípios, com referência 2024. Quase não há resíduo industrial (61 linhas) e não há empresas. Na v3 essa base passa a ser **contexto complementar**: mostra se o município da rota tem coleta seletiva, plano de gestão e metas, e o que ele já valoriza. Ela deixa de ser a fonte das rotas.

### 0.4 Cuidados de qualidade que o ETL vai tratar
1. Não há coordenadas. A localização de gerador e destinador é o **centróide do município (IBGE)**, e o app avisa o usuário disso. O cruzamento com o IBGE é feito por UF + nome normalizado (sem acento, em minúsculas).
2. Quantidades em kg são convertidas para toneladas. **Litros e unidades não são convertidos**: ficam na unidade original e são exibidos separados.
3. Valores numéricos no formato brasileiro (`30.000,00`) são convertidos para `numeric`.
4. Por padrão só entram estabelecimentos com situação cadastral "Ativa".
5. Para a oportunidade, vale a destinação mais recente de cada par (gerador, resíduo), e o app mostra o ano dela.

## 1. Definição de rota de valorização (v3)

- **Oportunidade:** um par (gerador, código de resíduo) cuja destinação mais recente foi **aterro** (D1, D4 ou D5).
- **Rota de valorização:** um **destinador** que, nos dados do RAPP, já recebeu o **mesmo código de resíduo** para uma operação **R** e fica dentro do raio escolhido a partir do gerador.
- **Contexto:** o resumo do município do destinador, vindo do diagnóstico municipal, quando o município estiver na base.

Isso cumpre a definição do Davi ("indústrias que destinam para aterros mas poderiam destinar para uma rota de valorização") com dados reais dos dois lados. Também deixa de ser necessária a tabela de-para "código de resíduo → material" da v2, porque o cruzamento é feito pelo próprio código.

## 2. Escopo do MVP: 3 funcionalidades

| # | Funcionalidade |
|---|---|
| F1 | **Listar oportunidades**: geradores que mandam resíduo para aterro e têm destinador valorizador no raio |
| F2 | **Mapa** de oportunidades e rotas |
| F3 | **Detalhe da oportunidade**: gerador, resíduo, quantidade, destinação atual, destinadores candidatos e contexto do município |

**Fora do MVP:** login e contas, cadastro manual, contato ou negociação com destinadores, marketplace, chat, notificações, favoritos, frete ou CO₂, histórico e gráficos por ano, exportação, painel administrativo e geocodificação por endereço.

**Usuário-alvo:** um consultor ou gestor ambiental, ou uma empresa de valorização procurando geradores que hoje mandam resíduo para aterro.

## 3. Histórias de usuário

### HU1: Listar oportunidades (F1)
**Como** consultor ambiental, **quero** ver quais geradores destinam resíduos a aterro e têm destinadores valorizadores próximos **para** priorizar quem abordar.

Critérios de aceitação:
1. Posso filtrar por UF/município (ou usar o GPS), por resíduo (busca por código ou descrição), por classe (perigoso ou não) e por raio (25, 50, 100, 250 ou 500 km; o padrão é 100 km).
2. Cada item mostra o gerador (razão social e município/UF), o resíduo (código e descrição), a quantidade com a unidade, o ano, a operação atual (ex.: "D5 – Aterro"), o número de destinadores valorizadores no raio e a distância do mais próximo.
3. Só aparecem oportunidades com pelo menos um destinador valorizador dentro do raio.
4. A lista vem ordenada por quantidade em toneladas (decrescente), com litros e unidades por último. Pode ser reordenada por distância e é paginada (20 por página).
5. **Loading:** aparece um skeleton enquanto a lista carrega.
6. **Vazio:** se nada for encontrado, aparece uma mensagem com os botões "Aumentar raio" e "Limpar filtros".
7. **Erro/offline:** sem conexão, aparece um banner "Você está offline" e o último resultado em cache, com a data. Se a API falhar, aparece uma mensagem com "Tentar novamente".

### HU2: Mapa (F2)
**Como** consultor ambiental, **quero** ver oportunidades e rotas no mapa **para** entender onde estão concentradas e a que distância ficam as rotas.

Critérios de aceitação:
1. Posso alternar entre Lista e Mapa mantendo os filtros e sem refazer a busca.
2. Geradores aparecem como marcadores agrupados por município (cluster), com o tamanho proporcional à quantidade. Um aviso fixo diz que a "localização é aproximada (centro do município)".
3. Tocar num gerador mostra os destinadores candidatos ligados por linhas e um cartão com o link para o detalhe (HU3).
4. **Loading, vazio e erro** seguem as mesmas regras da HU1. Se os tiles do mapa não carregarem offline, aparece um aviso e um botão para voltar à lista.

### HU3: Detalhe da oportunidade (F3)
**Como** consultor ambiental, **quero** ver a oportunidade e os destinadores candidatos **para** avaliar se a troca de destinação é viável.

Critérios de aceitação:
1. Mostra o gerador (razão social, CNPJ formatado, atividade, município/UF), o resíduo (código, descrição, perigoso ou não), a quantidade, a unidade, o ano e a operação atual.
2. Lista os destinadores candidatos ordenados por distância. Para cada um: razão social, CNPJ, município/UF, distância, operações R já usadas para esse código, quantidade já recebida desse código e ano mais recente.
3. Cada destinador mostra o contexto do seu município, se houver: coleta seletiva, plano de gestão (com link) e metas de reciclagem. Se o município não estiver no diagnóstico, aparece "Município sem diagnóstico".
4. Campos sem dado aparecem como "Não informado", nunca como 0.
5. Mostra as fontes (IBAMA RAPP e Diagnóstico Municipal) com as datas de atualização.
6. **Loading, vazio e erro:** skeleton enquanto carrega, e mensagem de erro com "Tentar novamente". Offline, o detalhe abre do cache se já tiver sido aberto antes.

## 4. Esquema do banco (PostgreSQL + PostGIS no Supabase)

### 4.1 Diagrama

```
uf 1─N municipio 1─N estabelecimento 1─N movimentacao_residuo (como gerador)
            │                       1─N movimentacao_residuo (como destinador)
            │                                  N─1 codigo_residuo
            │                                  N─1 operacao_destinacao
            │                                  N─1 fonte_dado
            │
            1─N declaracao 1─N geracao_residuo ─ composicao_material ─ destinacao_material   (contexto municipal)
                           1─N meta
```

### 4.2 Núcleo (IBAMA)

**`uf`**: sigla `char(2)` PK; nome `text` NOT NULL; nome_normalizado `text` UNIQUE (usado no cruzamento com "SAO PAULO", por exemplo).

**`municipio`** (IBGE): id_ibge `integer` PK; nome `text`; nome_normalizado `text`; uf_sigla FK → uf; geom `geography(Point,4326)` NOT NULL (centróide, GIST); UNIQUE (nome_normalizado, uf_sigla).

**`fonte_dado`**: id `smallint` PK; nome `text` UNIQUE; url `text`; atualizado_na_fonte `date`; importado_em `timestamptz` DEFAULT now().

**`estabelecimento`**
| Coluna | Tipo | Regra |
|---|---|---|
| cnpj | `char(14)` | PK (só dígitos) |
| razao_social | `text` | NOT NULL |
| municipio_id | `integer` | FK → municipio, NULL (quando o cruzamento falha, entra no relatório do ETL) |
| categoria_atividade | `text` | NULL (ex.: "Serviços de Utilidade") |
| detalhe_atividade | `text` | NULL |
| situacao_cadastral | `text` | NOT NULL |
| eh_gerador | `boolean` | NOT NULL DEFAULT false |
| eh_destinador | `boolean` | NOT NULL DEFAULT false |

A geometria vem de `municipio.geom`. Não há coluna própria no MVP; quando houver endereço, entra uma coluna `geom` opcional.

**`codigo_residuo`**: codigo `char(6)` PK (ex.: `170107`); descricao `text` NOT NULL; perigoso `boolean` NULL (vem de "Classificação Resíduo" no arquivo do gerador).

**`operacao_destinacao`**
| Coluna | Tipo | Regra |
|---|---|---|
| codigo | `varchar(3)` | PK (`R1` a `R13`, `D1` a `D15`) |
| descricao | `text` | NOT NULL |
| categoria | `operacao_categoria` (enum `valorizacao`, `aterro`, `eliminacao`) | NOT NULL. R* = valorização; D1, D4, D5 = aterro; demais D = eliminação |

**`movimentacao_residuo`**
| Coluna | Tipo | Regra |
|---|---|---|
| id | `bigint` identity | PK |
| gerador_cnpj | `char(14)` | FK → estabelecimento, NOT NULL |
| destinador_cnpj | `char(14)` | FK → estabelecimento, NOT NULL |
| codigo_residuo | `char(6)` | FK → codigo_residuo, NOT NULL |
| operacao | `varchar(3)` | FK → operacao_destinacao, NOT NULL |
| ano | `smallint` | NOT NULL |
| quantidade | `numeric(16,3)` | NULL, CHECK ≥ 0 |
| unidade | `unidade_medida` (enum `kg`, `l`, `un`) | NOT NULL |
| quantidade_ton | `numeric(16,3)` | GENERATED: `quantidade / 1000` quando a unidade é kg; NULL nas outras |
| fonte_id | `smallint` | FK → fonte_dado |
| | | UNIQUE (gerador_cnpj, destinador_cnpj, codigo_residuo, operacao, ano, unidade). Índices em (codigo_residuo, operacao) e em gerador_cnpj |

### 4.3 Contexto municipal (mantido da v2, só leitura)
As tabelas são `declaracao`, `tipo_residuo`, `material`, `destinacao`, `geracao_residuo`, `composicao_material`, `destinacao_material` e `meta`, com as mesmas colunas da v2 (seção 4.2 de `docs/historico/etapa-1-v2.md`). Elas se ligam ao núcleo por `municipio`. O app só usa no MVP o resumo do município (coleta seletiva, plano e metas), e as demais tabelas ficam carregadas para etapas futuras.

### 4.4 Camada de consulta
- **`mv_oportunidade`**: uma linha por (gerador, código) cuja movimentação mais recente foi `categoria = 'aterro'`. Colunas: quantidade, unidade, quantidade_ton, ano, operação e a geometria do município do gerador.
- **`mv_rota`**: uma linha por (destinador, código) com operação `valorizacao`. Colunas: operações (`text[]`), quantidade recebida por unidade, ano mais recente e a geometria do município do destinador. Índices GIST e B-tree em codigo_residuo.
- **Funções SQL:**
  - `listar_oportunidades(uf, municipio_id, lat, lon, codigo_residuo, perigoso, raio_km, ordem, limite, offset)`: faz o join de `mv_oportunidade` com `mv_rota` pelo código e por `ST_DWithin(raio)`. Retorna a contagem de rotas e a distância mínima.
  - `rotas_da_oportunidade(gerador_cnpj, codigo_residuo, raio_km)`: retorna os destinadores ordenados por `ST_Distance`.
- **RLS:** as tabelas são só leitura para `anon`, e a escrita é feita só pela service role do ETL.

> **Sobre LGPD:** CNPJ e razão social são dados de pessoa jurídica, já publicados pelo IBAMA como dados abertos. O app não guarda dados de pessoas físicas.

## 5. Arquitetura

```
IBAMA Destinador (73 MB) ─┐
IBAMA Gerador (826 MB, streaming) ─┼─► ETL Pandas ─► PostgreSQL/PostGIS ◄─ FastAPI (somente leitura) ◄─ App Expo
Base IBGE ─────────────────┤                                  /oportunidades, /oportunidades/{cnpj}/{codigo},
Diagnóstico municipal ─────┘                                  /residuos?q=, /municipios/{id}
```

- **ETL:** é idempotente, com um extrator por fonte. O arquivo do gerador é lido em pedaços (`chunksize`) e com seleção de colunas, para não estourar a memória. Os passos são: normalizar números e nomes, cruzar com o IBGE, classificar as operações, fazer upsert e atualizar as views. Gera relatórios de municípios sem cruzamento e CNPJs de gerador sem município.
- **API:** FastAPI + Pydantic v2 + SQLAlchemy 2 async/asyncpg, com erros num formato único.
- **App:** Expo Router + TypeScript estrito (sem `any`) + NativeWind. Usa TanStack Query com persistência offline, NetInfo, `expo-location` e `react-native-maps` (com cluster). Os tipos são gerados do OpenAPI.

### Estrutura de pastas

```
waste-colab/
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                   # config, logging, erros
│   │   ├── db/                     # engine/sessão async
│   │   ├── api/v1/                 # oportunidades.py, residuos.py, municipios.py
│   │   ├── schemas/                # modelos Pydantic de resposta
│   │   ├── repositories/           # chamadas às funções SQL
│   │   └── services/               # paginação, montagem do detalhe
│   ├── etl/
│   │   ├── run.py                  # python -m etl.run --fonte ibge|ibama-destinador|ibama-gerador|municipal
│   │   ├── extractors/             # ibge.py, ibama_destinador.py, ibama_gerador.py, municipal_sinir.py
│   │   ├── transform/              # números BR, normalização de nomes, cruzamento IBGE, classificação R/D
│   │   ├── load.py                 # upserts + refresh das views
│   │   └── reports/
│   ├── data/                       # arquivos brutos (fora do git)
│   └── tests/                      # api/ e etl/
├── supabase/
│   ├── migrations/                 # tabelas, enums, views, funções, RLS
│   └── seed/                       # uf, operacao_destinacao
└── mobile/
    ├── app/
    │   ├── _layout.tsx             # providers (Query, NetInfo)
    │   ├── index.tsx               # HU1: filtros + lista
    │   ├── mapa.tsx                # HU2
    │   └── oportunidade/[cnpj]/[codigo].tsx   # HU3
    └── src/
        ├── api/                    # cliente HTTP + tipos gerados
        ├── features/
        │   ├── oportunidades/      # HU1/HU2
        │   └── detalhe/            # HU3
        ├── components/ui/          # Skeleton, EmptyState, ErrorState, OfflineBanner
        ├── hooks/                  # useNetworkStatus, useUserLocation
        └── lib/                    # formatação (CNPJ, t, km), constantes
```

## 6. Decisões

| # | Decisão | Status |
|---|---|---|
| 1 | Oportunidade = gerador que destina a aterro (D1, D4, D5), conforme o RAPP | ✅ Definida pelo Davi |
| 1.1 | Fonte industrial = IBAMA RAPP | ✅ Escolhida pelo Davi |
| 1.2 | Rota = destinador do RAPP que já valoriza (R) o mesmo código de resíduo dentro do raio. A base municipal vira contexto | ✅ Confirmada pelo Davi |
| 2 | Classificação das destinações (agora com os códigos R/D) | ✅ Confirmada (adaptada) |
| 3 | Sem login no MVP | ✅ Confirmada |
| 4 | Localização pelo centróide do município (IBGE) | ✅ Confirmada |
| 5 | Vale o dado mais recente (declaração municipal e destinação por par gerador-resíduo) | ✅ Confirmada (estendida) |

## 7. Ajustes feitos na implementação (Etapa 2)

- **Dados de referência em migration:** UFs e operações R/D ficam em `…0250_dados_referencia.sql`, e não em `supabase/seed/`. O `seed.sql` do Supabase só roda localmente, e o app precisa dessas linhas em produção.
- **Busca pré-calculada:** além de `mv_oportunidade` e `mv_rota`, foram criadas `mv_oportunidade_rota` (pares oportunidade → destinador até 500 km, cerca de 580 mil linhas) e `mv_oportunidade_resumo` (contagem e distância mínima para os raios 25, 50, 100, 250 e 500 km). Um raio fora da lista é arredondado para o próximo. Com isso a busca nacional caiu de ~20 s para ~0,1 s.
- **Quantidades:** `quantidade_ton` é guardada com 3 casas decimais (precisão de 1 kg). Percentuais impossíveis no diagnóstico municipal (ex.: 2000%) viram "não informado".
- **Números da carga real:** 139 mil movimentações, 28,5 mil estabelecimentos e **23,8 mil oportunidades de 8,7 mil geradores**. Desses, 13,5 mil têm destinador valorizador a até 100 km. O número é menor que os 27,7 mil da análise inicial porque agora vale só a destinação do ano mais recente e entram só estabelecimentos ativos com município identificado.
