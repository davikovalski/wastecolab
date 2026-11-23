-- RLS: leitura pública (anon/authenticated); escrita só pela service role (ETL),
-- que ignora RLS no Supabase.
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
    execute format('alter table public.%I enable row level security', t);
    execute format('create policy leitura_publica on public.%I for select to anon, authenticated using (true)', t);
    execute format('revoke insert, update, delete, truncate on public.%I from anon, authenticated', t);
    execute format('grant select on public.%I to anon, authenticated', t);
  end loop;
end;
$$;

-- As funções de busca usam tipos e funções do PostGIS (schema extensions).
grant usage on schema extensions to anon, authenticated;

-- Views materializadas não têm RLS: o acesso é controlado por grant.
grant select on public.mv_oportunidade, public.mv_rota, public.mv_oportunidade_rota,
  public.mv_oportunidade_resumo, public.v_municipio_contexto
  to anon, authenticated;

grant execute on function public.listar_oportunidades(
  integer, char, integer, double precision, double precision, integer, char, boolean, text, integer, integer
) to anon, authenticated;
grant execute on function public.rotas_da_oportunidade(char, char, integer) to anon, authenticated;

revoke execute on function public.atualizar_views() from public, anon, authenticated;
