-- ClassMatch: country-free booking, tutor roles, tutor-owned availability, and timezone display.
-- Safe to run once in the Supabase SQL editor.
begin;

alter table public.session_requests
  drop column if exists student_country;
alter table public.session_requests
  add column if not exists student_timezone text not null default 'UTC';

alter table public.availability_slots
  drop constraint if exists availability_slots_timezone_check;

drop index if exists public.tutors_match_idx;
create index if not exists tutors_match_idx
on public.tutors(active, min_student_grade, max_student_grade)
where deleted_at is null;

create table if not exists public.tutor_roles (
  id uuid primary key default gen_random_uuid(),
  email text not null unique check (email = lower(trim(email))),
  tutor_id uuid not null unique references public.tutors(id) on delete cascade,
  timezone text not null default 'Asia/Damascus',
  timezone_confirmed boolean not null default false,
  assigned_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tutor_roles_email_idx on public.tutor_roles(lower(email));
alter table public.tutor_roles enable row level security;
revoke all on public.tutor_roles from anon, authenticated;
grant all on public.tutor_roles to service_role;
grant select on public.tutor_roles to authenticated;
grant update (timezone, timezone_confirmed) on public.tutor_roles to authenticated;

drop policy if exists "tutors read own role" on public.tutor_roles;
create policy "tutors read own role" on public.tutor_roles
for select to authenticated
using (email = lower(coalesce(auth.jwt() ->> 'email', '')));

drop policy if exists "tutors update own timezone" on public.tutor_roles;
create policy "tutors update own timezone" on public.tutor_roles
for update to authenticated
using (email = lower(coalesce(auth.jwt() ->> 'email', '')))
with check (email = lower(coalesce(auth.jwt() ->> 'email', '')));

drop policy if exists "authenticated availability" on public.availability_slots;
create policy "authenticated availability" on public.availability_slots
for select to authenticated
using (starts_at > now() - interval '1 year');

drop policy if exists "tutors insert own availability" on public.availability_slots;
create policy "tutors insert own availability" on public.availability_slots
for insert to authenticated
with check (exists (
  select 1 from public.tutor_roles r
  where r.tutor_id = availability_slots.tutor_id
    and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
) and availability_slots.status = 'open');

drop policy if exists "tutors update own availability" on public.availability_slots;
create policy "tutors update own availability" on public.availability_slots
for update to authenticated
using (availability_slots.status = 'open' and exists (
  select 1 from public.tutor_roles r
  where r.tutor_id = availability_slots.tutor_id
    and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
))
with check (exists (
  select 1 from public.tutor_roles r
  where r.tutor_id = availability_slots.tutor_id
    and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
) and availability_slots.status in ('open', 'cancelled'));

grant insert, update on public.availability_slots to authenticated;
grant select on public.availability_slots to authenticated;

drop policy if exists "requester history" on public.session_requests;
drop policy if exists "requester or assigned tutor history" on public.session_requests;
create policy "requester or assigned tutor history" on public.session_requests
for select to authenticated
using (
  requester_user_id = auth.uid()
  or exists (
    select 1 from public.tutor_roles r
    where r.tutor_id = session_requests.tutor_id
      and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
  )
);

grant select (
  id, tutor_id, slot_id, student_first_name, student_grade, subject,
  guardian_email, notes, status, meeting_url, created_at, requester_user_id,
  student_timezone
) on public.session_requests to authenticated;

create or replace function public.assign_tutor_role(
  p_tutor_id uuid,
  p_email text,
  p_actor_user_id uuid default null
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  role_id uuid;
  normalized_email text := lower(trim(p_email));
begin
  if normalized_email = '' then raise exception 'Tutor email is required'; end if;
  if not exists (select 1 from public.tutors where id = p_tutor_id and deleted_at is null) then
    raise exception 'Tutor not found';
  end if;
  delete from public.tutor_roles where email = normalized_email or tutor_id = p_tutor_id;
  update public.tutors set tutor_email = normalized_email where id = p_tutor_id;
  insert into public.tutor_roles(email, tutor_id, assigned_by)
  values (normalized_email, p_tutor_id, p_actor_user_id)
  returning id into role_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id, details)
  values ('assigned_tutor_role', 'tutor_role', role_id, p_actor_user_id, jsonb_build_object('tutor_id', p_tutor_id));
  return role_id;
end;
$$;

revoke all on function public.assign_tutor_role(uuid, text, uuid) from public, anon, authenticated;
grant execute on function public.assign_tutor_role(uuid, text, uuid) to service_role;

drop function if exists public.request_tutoring_session(uuid, uuid, text, text, smallint, text, text, text, text);
drop function if exists public.request_tutoring_session(uuid, uuid, text, text, smallint, text, text, text, text, uuid);

create or replace function public.request_tutoring_session(
  p_tutor_id uuid,
  p_slot_id uuid,
  p_student_first_name text,
  p_student_grade smallint,
  p_subject text,
  p_guardian_name text,
  p_guardian_email text,
  p_student_timezone text,
  p_notes text default ''
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  chosen_slot public.availability_slots%rowtype;
  chosen_tutor public.tutors%rowtype;
  request_id uuid;
  account_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if auth.uid() is null then raise exception 'Sign in is required'; end if;
  if account_email = '' or account_email <> lower(trim(p_guardian_email)) then
    raise exception 'The confirmation email must match the signed-in account';
  end if;
  if not exists (select 1 from pg_timezone_names where name = p_student_timezone) then
    raise exception 'Invalid student timezone';
  end if;
  if char_length(trim(p_student_first_name)) not between 1 and 50
     or char_length(trim(p_guardian_name)) not between 1 and 100
     or char_length(coalesce(p_notes, '')) > 1000 then
    raise exception 'Invalid request details';
  end if;
  if (select count(*) from public.session_requests where requester_user_id = auth.uid() and created_at > now() - interval '1 hour') >= 5 then
    raise exception 'Too many recent requests. Please wait before trying again';
  end if;
  select * into chosen_tutor from public.tutors
  where id = p_tutor_id and active = true and deleted_at is null;
  if chosen_tutor.id is null
     or p_student_grade not between chosen_tutor.min_student_grade and chosen_tutor.max_student_grade
     or not (p_subject = any(chosen_tutor.subjects)) then
    raise exception 'Tutor does not match this request';
  end if;
  select * into chosen_slot from public.availability_slots
  where id = p_slot_id and tutor_id = p_tutor_id for update;
  if chosen_slot.id is null or chosen_slot.status <> 'open' or chosen_slot.starts_at <= now() then
    raise exception 'That time is no longer available';
  end if;
  insert into public.session_requests (
    tutor_id, slot_id, student_first_name, student_grade, subject,
    guardian_name, guardian_email, requester_user_id, notes, student_timezone
  ) values (
    p_tutor_id, p_slot_id, trim(p_student_first_name), p_student_grade, p_subject,
    trim(p_guardian_name), account_email, auth.uid(), coalesce(trim(p_notes), ''), p_student_timezone
  ) returning id into request_id;
  update public.availability_slots set status = 'requested' where id = p_slot_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id)
  values ('created', 'session_request', request_id, auth.uid());
  return request_id;
end;
$$;

revoke all on function public.request_tutoring_session(uuid, uuid, text, smallint, text, text, text, text, text) from public, anon;
grant execute on function public.request_tutoring_session(uuid, uuid, text, smallint, text, text, text, text, text) to authenticated;

commit;
