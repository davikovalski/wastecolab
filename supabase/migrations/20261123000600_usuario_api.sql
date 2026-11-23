-- Usuário de banco só de leitura para a API (FastAPI).
-- Criado sem senha. Para ativar, rode uma vez no SQL Editor do Supabase:
--   alter role api_leitura with login password '<senha forte>';
-- Pelo pooler do Supabase o usuário fica "api_leitura.<project-ref>".
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'api_leitura') then
    create role api_leitura nologin;
  end if;
end;
$$;

grant usage on schema public, extensions to api_leitura;

-- Mesmas tabelas que o anon lê; a política de RLS passa a incluir a API.
do $$
declare
  t text;
begin
  foreach t in array array[
    'uf', 'municipio', 'fonte_dado', 'estabelecimento', 'codigo_residuo',
    'operacao_destinacao', 'movimentacao_residuo', 'declaracao', 'tipo_residuo',
    'material', 'destinacao', 'geracao_residuo', 'composicao_material',
    'destinacao_material', 'meta'
  ]
  loop
    execute format('grant select on public.%I to api_leitura', t);
    execute format('alter policy leitura_publica on public.%I to anon, authenticated, api_leitura', t);
  end loop;
end;
$$;

grant select on public.mv_oportunidade, public.mv_rota, public.mv_oportunidade_rota,
  public.mv_oportunidade_resumo, public.v_municipio_contexto to api_leitura;

grant execute on function public.listar_oportunidades(
  integer, char, integer, double precision, double precision, integer, char, boolean, text, integer, integer
) to api_leitura;
grant execute on function public.rotas_da_oportunidade(char, char, integer) to api_leitura;

-- Evita que o usuário da API fique preso em consultas longas.
alter role api_leitura set statement_timeout = '10s';
