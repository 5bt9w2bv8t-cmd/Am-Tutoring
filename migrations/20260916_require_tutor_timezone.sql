-- Require every assigned tutor to confirm their own timezone.
alter table public.tutor_roles
  add column if not exists timezone_confirmed boolean not null default false;

revoke update on public.tutor_roles from authenticated;
grant update (timezone, timezone_confirmed) on public.tutor_roles to authenticated;
