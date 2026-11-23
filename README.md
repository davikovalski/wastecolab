# Waste Colab

Aplicativo para encontrar **rotas de valorização** para resíduos industriais: geradores que hoje
mandam resíduos para aterro e destinadores que já valorizam aquele mesmo resíduo por perto.

Escopo, histórias de usuário e decisões: [`docs/etapa-1-escopo-e-arquitetura.md`](docs/etapa-1-escopo-e-arquitetura.md).

| Pasta | Conteúdo | Estado |
|---|---|---|
| `supabase/` | Migrations do PostgreSQL/PostGIS (Supabase) | Etapa 2 |
| `backend/etl/` | ETL em Python + Pandas | Etapa 2 |
| `backend/app/` | API FastAPI | próxima etapa |
| `mobile/` | App Expo + TypeScript + NativeWind | próxima etapa |

## Banco de dados (`supabase/migrations`)

| Migration | O que cria |
|---|---|
| `…0100_extensoes_e_tipos` | PostGIS (schema `extensions`) e enums |
| `…0200_nucleo_ibama` | `uf`, `municipio`, `fonte_dado`, `estabelecimento`, `codigo_residuo`, `operacao_destinacao`, `movimentacao_residuo` |
| `…0250_dados_referencia` | As 27 UFs e as operações R1–R13 / D1–D15 já classificadas (valorização, aterro, eliminação) |
| `…0300_contexto_municipal` | Tabelas do diagnóstico municipal (`declaracao`, `meta`, …) |
| `…0400_consultas` | Views materializadas e as funções `listar_oportunidades`, `rotas_da_oportunidade` e `atualizar_views` |
| `…0500_seguranca` | RLS: leitura para `anon`/`authenticated`; escrita só pela service role |

Os dados de referência estão numa migration (e não no `seed.sql`) porque o seed do Supabase só roda
em ambiente local, e o app precisa dessas linhas em produção.

**Como a busca é rápida:** `mv_oportunidade` (aterro) e `mv_rota` (valorização) são cruzadas uma
única vez em `mv_oportunidade_rota` (pares até 500 km) e resumidas em `mv_oportunidade_resumo` para os
raios do app (25, 50, 100, 250 e 500 km). Um raio fora dessa lista é arredondado para o próximo.

Aplicar no Supabase: `supabase db push` (com o projeto já vinculado por `supabase link`).

## ETL (`backend/`)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # preencha DATABASE_URL (conexão direta, usuário postgres)

python -m etl.run todas --municipal "caminho/Municipal - Diagnostico.csv"
```

- Baixa sozinho os arquivos do IBAMA (destinador ~73 MB e gerador ~830 MB) e a base de municípios
  para `backend/data/`, e reaproveita o que já foi baixado (`--baixar-novamente` força o download).
- Etapas separadas: `python -m etl.run ibge | ibama | municipal`. `--sem-gerador` pula o arquivo
  grande, mas aí os geradores ficam sem município e não viram oportunidade.
- Pode ser repetido: usa upsert e substitui as movimentações da fonte a cada carga.
- Gera relatórios em `backend/relatorios/` (linhas rejeitadas, estabelecimentos sem município).
- Carga completa num Postgres local: cerca de 70 segundos, com pico de ~270 MB de memória.

## Testes

```bash
cd backend
pytest tests/etl                                   # unitários
TEST_DATABASE_URL=postgresql://... pytest tests/integracao   # ATENÇÃO: apaga os schemas public e extensions desse banco
ruff check . && mypy
```

Para rodar a integração localmente, crie um banco vazio com PostGIS disponível; o teste aplica
`supabase/local/roles.sql` (cria as roles `anon`, `authenticated` e `service_role` que o Supabase já tem)
e todas as migrations.

## Fontes de dados

- IBAMA, Dados Abertos do RAPP: Resíduos Sólidos – Destinador e Gerador (dadosabertos.ibama.gov.br).
- Municípios e centróides: [kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros)
  (derivado do IBGE, licença MIT).
- Diagnóstico municipal de resíduos sólidos (arquivo fornecido pelo projeto).
