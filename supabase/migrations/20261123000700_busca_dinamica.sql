-- listar_oportunidades em PL/pgSQL com SQL dinâmico.
-- A versão em SQL puro usava filtros do tipo "(p_x is null or ...)"; chamada pela API, o
-- planejador estimava 1 linha e escolhia loops aninhados (~4 s). Montando só os filtros
-- informados, cada chamada ganha um plano próprio (~0,1 s). Mesma assinatura e mesmo retorno.
create or replace function public.listar_oportunidades(
  p_raio_km          integer  default 100,
  p_uf               char(2)  default null,
  p_municipio_id     integer  default null,
  p_lat              double precision default null,
  p_lon              double precision default null,
  p_raio_local_km    integer  default 50,
  p_codigo_residuo   char(6)  default null,
  p_perigoso         boolean  default null,
  p_ordem            text     default 'quantidade',
  p_limite           integer  default 20,
  p_offset           integer  default 0
)
returns table (
  gerador_cnpj               char(14),
  razao_social               text,
  municipio_id               integer,
  municipio_nome             text,
  uf_sigla                   char(2),
  codigo_residuo             char(6),
  residuo_descricao          text,
  perigoso                   boolean,
  ano                        smallint,
  operacoes                  varchar[],
  quantidade_ton             numeric,
  quantidade_l               numeric,
  quantidade_un              numeric,
  n_rotas                    bigint,
  distancia_rota_proxima_km  double precision,
  lat                        double precision,
  lon                        double precision,
  total                      bigint
)
language plpgsql
stable
set search_path = public, extensions
as $$
declare
  v_raio   smallint;
  v_filtro text := '';
  v_ordem  text;
begin
  -- Arredonda para o raio pré-calculado imediatamente acima (máximo 500 km).
  select min(k) into v_raio
  from (values (25), (50), (100), (250), (500)) as raios(k)
  where k >= least(greatest(p_raio_km, 1), 500);

  if p_uf is not null then
    v_filtro := v_filtro || ' and mu.uf_sigla = $1';
  end if;
  if p_municipio_id is not null then
    v_filtro := v_filtro || ' and o.municipio_id = $2';
  end if;
  if p_lat is not null and p_lon is not null then
    v_filtro := v_filtro
      || ' and st_dwithin(o.geom, st_setsrid(st_makepoint($4, $3), 4326)::geography, $5 * 1000.0)';
  end if;
  if p_codigo_residuo is not null then
    v_filtro := v_filtro || ' and o.codigo_residuo = $6';
  end if;
  if p_perigoso is not null then
    v_filtro := v_filtro || ' and cr.perigoso = $7';
  end if;

  v_ordem := case when p_ordem = 'distancia' then 'rs.distancia_km asc, ' else '' end
    || 'o.quantidade_ton desc nulls last, o.quantidade_l desc nulls last, '
    || 'o.quantidade_un desc nulls last, o.gerador_cnpj, o.codigo_residuo';

  return query execute format(
    $sql$
    select
      o.gerador_cnpj, e.razao_social, o.municipio_id, mu.nome, mu.uf_sigla,
      o.codigo_residuo, cr.descricao, cr.perigoso, o.ano, o.operacoes,
      o.quantidade_ton, o.quantidade_l, o.quantidade_un,
      rs.n_rotas, rs.distancia_km::double precision,
      st_y(o.geom::geometry), st_x(o.geom::geometry),
      count(*) over ()
    from public.mv_oportunidade_resumo rs
    join public.mv_oportunidade o
      on o.gerador_cnpj = rs.gerador_cnpj and o.codigo_residuo = rs.codigo_residuo
    join public.estabelecimento e on e.cnpj = o.gerador_cnpj
    join public.municipio mu on mu.id_ibge = o.municipio_id
    join public.codigo_residuo cr on cr.codigo = o.codigo_residuo
    where rs.raio_km = $8 %s
    order by %s
    limit $9 offset $10
    $sql$,
    v_filtro, v_ordem
  )
  using p_uf, p_municipio_id, p_lat, p_lon, p_raio_local_km, p_codigo_residuo, p_perigoso,
        v_raio, least(greatest(p_limite, 1), 100), greatest(p_offset, 0);
end;
$$;
