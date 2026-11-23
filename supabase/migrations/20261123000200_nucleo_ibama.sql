-- Núcleo do MVP: localidades (IBGE) e movimentações de resíduos (IBAMA RAPP).
set search_path = public, extensions;

create table public.uf (
  sigla            char(2)  primary key,
  codigo_ibge      smallint not null unique,
  nome             text     not null,
  nome_normalizado text     not null unique
);

create table public.municipio (
  id_ibge          integer  primary key,
  nome             text     not null,
  nome_normalizado text     not null,
  uf_sigla         char(2)  not null references public.uf (sigla),
  geom             extensions.geography(point, 4326) not null,
  constraint municipio_nome_uf_key unique (nome_normalizado, uf_sigla)
);
create index municipio_geom_idx on public.municipio using gist (geom);

create table public.fonte_dado (
  id                  smallint generated always as identity primary key,
  nome                text        not null unique,
  url                 text,
  atualizado_na_fonte date,
  importado_em        timestamptz not null default now()
);

create table public.estabelecimento (
  cnpj                char(14) primary key check (cnpj ~ '^[0-9]{14}$'),
  razao_social        text     not null,
  municipio_id        integer  references public.municipio (id_ibge),
  categoria_atividade text,
  detalhe_atividade   text,
  situacao_cadastral  text     not null,
  eh_gerador          boolean  not null default false,
  eh_destinador       boolean  not null default false
);
create index estabelecimento_municipio_idx on public.estabelecimento (municipio_id);

create table public.codigo_residuo (
  codigo    char(6) primary key check (codigo ~ '^[0-9]{6}$'),
  descricao text    not null,
  perigoso  boolean
);

create table public.operacao_destinacao (
  codigo    varchar(3) primary key check (codigo ~ '^[RD][0-9]{1,2}$'),
  descricao text       not null,
  categoria public.operacao_categoria not null
);

create table public.movimentacao_residuo (
  id              bigint generated always as identity primary key,
  gerador_cnpj    char(14)   not null references public.estabelecimento (cnpj),
  destinador_cnpj char(14)   not null references public.estabelecimento (cnpj),
  codigo_residuo  char(6)    not null references public.codigo_residuo (codigo),
  operacao        varchar(3) not null references public.operacao_destinacao (codigo),
  ano             smallint   not null check (ano between 2000 and 2100),
  quantidade      numeric(16, 3) check (quantidade >= 0),
  unidade         public.unidade_medida not null,
  quantidade_ton  numeric(16, 3) generated always as (
                    case when unidade = 'kg' then quantidade / 1000 end
                  ) stored,
  fonte_id        smallint   not null references public.fonte_dado (id),
  constraint movimentacao_residuo_chave unique
    (gerador_cnpj, destinador_cnpj, codigo_residuo, operacao, ano, unidade)
);
create index movimentacao_codigo_operacao_idx on public.movimentacao_residuo (codigo_residuo, operacao);
create index movimentacao_gerador_idx on public.movimentacao_residuo (gerador_cnpj);
create index movimentacao_destinador_idx on public.movimentacao_residuo (destinador_cnpj);
