-- Camada de consulta: oportunidades (aterro) e rotas (valorização).
set search_path = public, extensions;

-- Oportunidade: par (gerador, resíduo) cuja movimentação do ano mais recente
-- inclui destinação a aterro (D1, D4, D5).
create materialized view public.mv_oportunidade as
with ultimo_ano as (
  select m.gerador_cnpj, m.codigo_residuo, max(m.ano) as ano
  from public.movimentacao_residuo m
  group by m.gerador_cnpj, m.codigo_residuo
)
select
  m.gerador_cnpj,
  m.codigo_residuo,
  u.ano,
  array_agg(distinct m.operacao order by m.operacao)          as operacoes,
  sum(m.quantidade_ton)                                        as quantidade_ton,
  sum(m.quantidade) filter (where m.unidade = 'l')             as quantidade_l,
  sum(m.quantidade) filter (where m.unidade = 'un')            as quantidade_un,
  e.municipio_id,
  mu.geom
from public.movimentacao_residuo m
join ultimo_ano u
  on u.gerador_cnpj = m.gerador_cnpj and u.codigo_residuo = m.codigo_residuo and u.ano = m.ano
join public.operacao_destinacao od on od.codigo = m.operacao and od.categoria = 'aterro'
join public.estabelecimento e on e.cnpj = m.gerador_cnpj and e.situacao_cadastral = 'Ativa'
join public.municipio mu on mu.id_ibge = e.municipio_id
group by m.gerador_cnpj, m.codigo_residuo, u.ano, e.municipio_id, mu.geom;

create unique index mv_oportunidade_chave on public.mv_oportunidade (gerador_cnpj, codigo_residuo);
create index mv_oportunidade_geom_idx on public.mv_oportunidade using gist (geom);
create index mv_oportunidade_codigo_idx on public.mv_oportunidade (codigo_residuo);

-- Rota: par (destinador, resíduo) com pelo menos uma operação de valorização (R).
create materialized view public.mv_rota as
select
  m.destinador_cnpj,
  m.codigo_residuo,
  array_agg(distinct m.operacao order by m.operacao)          as operacoes,
  max(m.ano)                                                   as ano_mais_recente,
  sum(m.quantidade_ton)                                        as quantidade_ton,
  sum(m.quantidade) filter (where m.unidade = 'l')             as quantidade_l,
  sum(m.quantidade) filter (where m.unidade = 'un')            as quantidade_un,
  e.municipio_id,
  mu.geom
from public.movimentacao_residuo m
join public.operacao_destinacao od on od.codigo = m.operacao and od.categoria = 'valorizacao'
join public.estabelecimento e on e.cnpj = m.destinador_cnpj and e.situacao_cadastral = 'Ativa'
join public.municipio mu on mu.id_ibge = e.municipio_id
group by m.destinador_cnpj, m.codigo_residuo, e.municipio_id, mu.geom;

create unique index mv_rota_chave on public.mv_rota (destinador_cnpj, codigo_residuo);
create index mv_rota_geom_idx on public.mv_rota using gist (geom);
create index mv_rota_codigo_idx on public.mv_rota (codigo_residuo);

-- Pares oportunidade -> rota pré-calculados até o raio máximo do app (500 km).
-- Evita calcular distâncias geográficas a cada busca.
create materialized view public.mv_oportunidade_rota as
select
  o.gerador_cnpj,
  o.codigo_residuo,
  r.destinador_cnpj,
  (st_distance(o.geom, r.geom) / 1000.0)::real as distancia_km
from public.mv_oportunidade o
join public.mv_rota r
  on r.codigo_residuo = o.codigo_residuo
 and r.destinador_cnpj <> o.gerador_cnpj
 and st_dwithin(o.geom, r.geom, 500000);

create unique index mv_oportunidade_rota_chave
  on public.mv_oportunidade_rota (gerador_cnpj, codigo_residuo, destinador_cnpj);
create index mv_oportunidade_rota_distancia_idx
  on public.mv_oportunidade_rota (distancia_km) include (gerador_cnpj, codigo_residuo);

-- Resumo por raio (os raios do app são fixos: 25, 50, 100, 250, 500 km).
create materialized view public.mv_oportunidade_resumo as
select
  p.gerador_cnpj,
  p.codigo_residuo,
  raio.km::smallint      as raio_km,
  count(*)               as n_rotas,
  min(p.distancia_km)    as distancia_km
from public.mv_oportunidade_rota p
join (values (25), (50), (100), (250), (500)) as raio(km) on p.distancia_km <= raio.km
group by p.gerador_cnpj, p.codigo_residuo, raio.km;

create unique index mv_oportunidade_resumo_chave
  on public.mv_oportunidade_resumo (raio_km, gerador_cnpj, codigo_residuo);

-- Resumo do município (contexto da HU3), a partir da declaração vigente.
create view public.v_municipio_contexto
with (security_invoker = true) as
select
  d.municipio_id,
  d.id                       as declaracao_id,
  d.ano_referencia,
  d.possui_coleta_seletiva,
  d.possui_plano_gestao,
  d.link_plano,
  d.ano_ultima_versao_plano,
  coalesce(
    (select jsonb_agg(jsonb_build_object(
              'tipo', mt.tipo,
              'valor_atual', mt.valor_atual,
              'valor_meta', mt.valor_meta,
              'prazo_texto', mt.prazo_texto,
              'prazo_ano', mt.prazo_ano,
              'programa', mt.programa
            ) order by mt.tipo)
     from public.meta mt where mt.declaracao_id = d.id),
    '[]'::jsonb
  ) as metas
from public.declaracao d
where d.vigente;

-- HU1/HU2: lista paginada de oportunidades com rotas dentro do raio.
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
language sql
stable
set search_path = public, extensions
as $$
  with candidatas as (
    select o.*
    from public.mv_oportunidade o
    join public.municipio mu on mu.id_ibge = o.municipio_id
    join public.codigo_residuo cr on cr.codigo = o.codigo_residuo
    where (p_uf is null or mu.uf_sigla = p_uf)
      and (p_municipio_id is null or o.municipio_id = p_municipio_id)
      and (p_lat is null or p_lon is null
           or st_dwithin(o.geom, st_setsrid(st_makepoint(p_lon, p_lat), 4326)::geography, p_raio_local_km * 1000.0))
      and (p_codigo_residuo is null or o.codigo_residuo = p_codigo_residuo)
      and (p_perigoso is null or cr.perigoso = p_perigoso)
  ),
  com_rotas as (
    select rs.gerador_cnpj, rs.codigo_residuo, rs.n_rotas, rs.distancia_km
    from public.mv_oportunidade_resumo rs
    where rs.raio_km = (
      -- Arredonda para o raio pré-calculado imediatamente acima (máximo 500 km).
      select min(k) from (values (25), (50), (100), (250), (500)) as raios(k) where k >= least(p_raio_km, 500)
    )
  )
  select
    c.gerador_cnpj, e.razao_social, c.municipio_id, mu.nome, mu.uf_sigla,
    c.codigo_residuo, cr.descricao, cr.perigoso, c.ano, c.operacoes,
    c.quantidade_ton, c.quantidade_l, c.quantidade_un,
    cw.n_rotas, cw.distancia_km::double precision,
    st_y(c.geom::geometry), st_x(c.geom::geometry),
    count(*) over ()
  from candidatas c
  join com_rotas cw on cw.gerador_cnpj = c.gerador_cnpj and cw.codigo_residuo = c.codigo_residuo
  join public.estabelecimento e on e.cnpj = c.gerador_cnpj
  join public.municipio mu on mu.id_ibge = c.municipio_id
  join public.codigo_residuo cr on cr.codigo = c.codigo_residuo
  order by
    case when p_ordem = 'distancia' then cw.distancia_km end asc nulls last,
    c.quantidade_ton desc nulls last,
    c.quantidade_l desc nulls last,
    c.quantidade_un desc nulls last,
    c.gerador_cnpj, c.codigo_residuo
  limit least(greatest(p_limite, 1), 100)
  offset greatest(p_offset, 0);
$$;

-- HU3: destinadores candidatos de uma oportunidade, por distância.
create or replace function public.rotas_da_oportunidade(
  p_gerador_cnpj   char(14),
  p_codigo_residuo char(6),
  p_raio_km        integer default 100
)
returns table (
  destinador_cnpj   char(14),
  razao_social      text,
  municipio_id      integer,
  municipio_nome    text,
  uf_sigla          char(2),
  distancia_km      double precision,
  operacoes         varchar[],
  ano_mais_recente  smallint,
  quantidade_ton    numeric,
  quantidade_l      numeric,
  quantidade_un     numeric,
  lat               double precision,
  lon               double precision
)
language sql
stable
set search_path = public, extensions
as $$
  select
    r.destinador_cnpj, e.razao_social, r.municipio_id, mu.nome, mu.uf_sigla,
    p.distancia_km::double precision,
    r.operacoes, r.ano_mais_recente, r.quantidade_ton, r.quantidade_l, r.quantidade_un,
    st_y(r.geom::geometry), st_x(r.geom::geometry)
  from public.mv_oportunidade_rota p
  join public.mv_rota r
    on r.destinador_cnpj = p.destinador_cnpj and r.codigo_residuo = p.codigo_residuo
  join public.estabelecimento e on e.cnpj = r.destinador_cnpj
  join public.municipio mu on mu.id_ibge = r.municipio_id
  where p.gerador_cnpj = p_gerador_cnpj
    and p.codigo_residuo = p_codigo_residuo
    and p.distancia_km <= least(greatest(p_raio_km, 1), 500)
  order by p.distancia_km, r.destinador_cnpj;
$$;

-- Chamada pelo ETL depois de cada carga.
create or replace function public.atualizar_views()
returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
begin
  refresh materialized view concurrently public.mv_oportunidade;
  refresh materialized view concurrently public.mv_rota;
  refresh materialized view concurrently public.mv_oportunidade_rota;
  refresh materialized view concurrently public.mv_oportunidade_resumo;
end;
$$;
