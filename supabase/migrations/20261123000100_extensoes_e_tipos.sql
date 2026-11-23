-- Extensões e tipos enumerados do Waste Colab.
-- No Supabase o PostGIS fica no schema "extensions".

create schema if not exists extensions;
create extension if not exists postgis with schema extensions;

-- Categoria da operação de destinação (códigos R/D do RAPP/IBAMA).
create type public.operacao_categoria as enum ('valorizacao', 'aterro', 'eliminacao');

-- Unidade de medida informada no RAPP.
create type public.unidade_medida as enum ('kg', 'l', 'un');

-- Tipos de meta do diagnóstico municipal.
create type public.meta_tipo as enum (
  'coleta_seletiva',
  'reciclagem',
  'reducao',
  'reutilizacao',
  'eliminacao_lixoes'
);
