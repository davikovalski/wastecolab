-- Só para validar as migrations num PostgreSQL local (fora do Supabase).
-- No Supabase essas roles já existem.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end;
$$;

-- No Supabase o schema public já é acessível a essas roles.
grant usage on schema public to anon, authenticated, service_role;
