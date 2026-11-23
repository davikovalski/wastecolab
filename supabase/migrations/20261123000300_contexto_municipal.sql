-- Contexto municipal (Diagnóstico Municipal / SINIR). Só leitura no app.
set search_path = public, extensions;

create table public.declaracao (
  id                          integer  primary key,
  municipio_id                integer  not null references public.municipio (id_ibge),
  fonte_id                    smallint not null references public.fonte_dado (id),
  declarante                  text     not null,
  ano                         smallint not null,
  ano_referencia              smallint not null,
  data_criacao                date     not null,
  data_entrega                date     not null,
  possui_coleta_seletiva      boolean  not null,
  possui_plano_gestao         boolean  not null,
  link_plano                  text,
  periodicidade_revisao_texto text,
  periodicidade_revisao_anos  smallint check (periodicidade_revisao_anos between 0 and 30),
  ano_ultima_versao_plano     smallint,
  vigente                     boolean  not null default false
);
create index declaracao_municipio_idx on public.declaracao (municipio_id);
create unique index declaracao_vigente_por_municipio on public.declaracao (municipio_id) where vigente;

create table public.tipo_residuo (
  id        smallint generated always as identity primary key,
  descricao text not null unique
);

create table public.material (
  id              smallint generated always as identity primary key,
  descricao       text not null unique,
  tipo_residuo_id smallint references public.tipo_residuo (id)
);

create table public.destinacao (
  id        smallint generated always as identity primary key,
  descricao text not null unique,
  categoria public.operacao_categoria not null
);

create table public.geracao_residuo (
  id              bigint generated always as identity primary key,
  declaracao_id   integer  not null references public.declaracao (id) on delete cascade,
  tipo_residuo_id smallint not null references public.tipo_residuo (id),
  massa_ton       numeric(14, 3) check (massa_ton >= 0),
  constraint geracao_residuo_chave unique (declaracao_id, tipo_residuo_id)
);

create table public.composicao_material (
  id          bigint generated always as identity primary key,
  geracao_id  bigint   not null references public.geracao_residuo (id) on delete cascade,
  material_id smallint not null references public.material (id),
  percentual  numeric(5, 2) check (percentual between 0 and 100),
  constraint composicao_material_chave unique (geracao_id, material_id)
);

create table public.destinacao_material (
  id            bigint generated always as identity primary key,
  composicao_id bigint   not null references public.composicao_material (id) on delete cascade,
  destinacao_id smallint not null references public.destinacao (id),
  percentual    numeric(5, 2) check (percentual between 0 and 100),
  constraint destinacao_material_chave unique (composicao_id, destinacao_id)
);

create table public.meta (
  id                  bigint generated always as identity primary key,
  declaracao_id       integer not null references public.declaracao (id) on delete cascade,
  tipo                public.meta_tipo not null,
  valor_atual         numeric(14, 3),
  valor_meta          numeric(14, 3),
  prazo_texto         text,
  prazo_ano           smallint,
  programa            text,
  programa_descritivo text
);
create index meta_declaracao_idx on public.meta (declaracao_id);
