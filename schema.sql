-- ClassMatch production schema. Safe to rerun.
begin;

create extension if not exists pgcrypto;

create table if not exists public.tutors (
  id uuid primary key default gen_random_uuid(),
  full_name text not null check (char_length(trim(full_name)) between 1 and 80),
  tutor_email text not null check (tutor_email = lower(trim(tutor_email))),
  age smallint not null check (age between 1 and 120),
  school_grade smallint check (school_grade between 1 and 12),
  country text not null,
  subjects text[] not null check (cardinality(subjects) > 0),
  languages text[] not null check (cardinality(languages) > 0),
  min_student_grade smallint not null check (min_student_grade between 1 and 12),
  max_student_grade smallint not null check (max_student_grade between min_student_grade and 12),
  bio text not null check (char_length(bio) between 1 and 800),
  active boolean not null default true,
  approved_at timestamptz not null default now(),
  deleted_at timestamptz
);

-- Compatibility with the earlier prototype schema.
do $$
begin
  alter table public.tutors add column if not exists deleted_at timestamptz;
  alter table public.tutors alter column school_grade drop not null;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'tutors' and column_name = 'guardian_email') then
    alter table public.tutors alter column guardian_email drop not null;
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'tutors' and column_name = 'city') then
    alter table public.tutors alter column city drop not null;
  end if;
end $$;

-- Bring older tutor tables up to the current worldwide rules.
alter table public.tutors drop constraint if exists tutors_country_check;
alter table public.tutors drop constraint if exists tutors_age_check;
alter table public.tutors drop constraint if exists tutors_age_valid_check;
alter table public.tutors
  add constraint tutors_age_valid_check check (age between 1 and 120);

create table if not exists public.availability_slots (
  id uuid primary key default gen_random_uuid(),
  tutor_id uuid not null references public.tutors(id) on delete cascade,
  starts_at timestamptz not null,
  ends_at timestamptz not null check (ends_at > starts_at),
  timezone text not null,
  status text not null default 'open' check (status in ('open', 'requested', 'booked', 'cancelled')),
  created_at timestamptz not null default now(),
  unique (tutor_id, starts_at)
);

create table if not exists public.session_requests (
  id uuid primary key default gen_random_uuid(),
  tutor_id uuid not null references public.tutors(id),
  slot_id uuid not null references public.availability_slots(id),
  student_first_name text not null check (char_length(trim(student_first_name)) between 1 and 50),
  student_grade smallint not null check (student_grade between 1 and 12),
  subject text not null check (char_length(subject) between 1 and 60),
  guardian_name text not null check (char_length(trim(guardian_name)) between 1 and 100),
  guardian_email text not null check (guardian_email = lower(trim(guardian_email))),
  requester_user_id uuid not null references auth.users(id) on delete cascade,
  notes text not null default '' check (char_length(notes) <= 1000),
  status text not null default 'requested' check (status in ('requested', 'confirmed', 'cancelled', 'completed', 'declined')),
  meeting_url text check (meeting_url is null or meeting_url ~ '^https://[^[:space:]]+$'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.session_requests drop column if exists student_country;
alter table public.session_requests add column if not exists student_timezone text not null default 'UTC';
alter table public.availability_slots drop constraint if exists availability_slots_timezone_check;

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

alter table public.tutor_roles
  add column if not exists timezone_confirmed boolean not null default false;

create table if not exists public.email_events (
  id bigint generated always as identity primary key,
  event_type text not null,
  recipient text not null,
  subject text not null,
  status text not null check (status in ('sent', 'failed')),
  provider_message_id text,
  error text,
  related_id uuid,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_log (
  id bigint generated always as identity primary key,
  action text not null,
  record_type text not null,
  record_id uuid,
  actor_user_id uuid,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Social sign-in was removed; this obsolete PKCE scratch table contains no user records.
drop table if exists public.oauth_flows;

create unique index if not exists one_active_request_per_slot on public.session_requests(slot_id) where status in ('requested', 'confirmed');
create unique index if not exists tutors_email_unique on public.tutors(lower(tutor_email));
drop index if exists public.tutors_match_idx;
create index if not exists tutors_match_idx on public.tutors(active, min_student_grade, max_student_grade) where deleted_at is null;
create index if not exists tutor_roles_email_idx on public.tutor_roles(lower(email));
create index if not exists tutors_subjects_idx on public.tutors using gin(subjects);
create index if not exists availability_upcoming_idx on public.availability_slots(tutor_id, starts_at) where status in ('open', 'requested', 'booked');
create index if not exists session_requester_created_idx on public.session_requests(requester_user_id, created_at desc);
create index if not exists session_tutor_created_idx on public.session_requests(tutor_id, created_at desc);
create index if not exists session_status_created_idx on public.session_requests(status, created_at desc);
create index if not exists email_events_related_idx on public.email_events(related_id, created_at desc);

alter table public.tutors enable row level security;
alter table public.availability_slots enable row level security;
alter table public.session_requests enable row level security;
alter table public.email_events enable row level security;
alter table public.audit_log enable row level security;
alter table public.tutor_roles enable row level security;
revoke all on public.tutors, public.availability_slots, public.session_requests, public.email_events, public.audit_log, public.tutor_roles from anon, authenticated;
grant all on public.tutors, public.availability_slots, public.session_requests, public.email_events, public.audit_log, public.tutor_roles to service_role;
grant usage, select on all sequences in schema public to service_role;
grant select (id, full_name) on public.tutors to authenticated;
grant select (id, starts_at, ends_at, timezone, status) on public.availability_slots to authenticated;
grant select (id, tutor_id, slot_id, student_first_name, subject, status, meeting_url, created_at, requester_user_id) on public.session_requests to authenticated;
grant select on public.tutor_roles to authenticated;
grant update (timezone, timezone_confirmed) on public.tutor_roles to authenticated;
grant insert, update on public.availability_slots to authenticated;
grant select on public.availability_slots to authenticated;
grant select (student_grade, guardian_email, notes, student_timezone) on public.session_requests to authenticated;

drop policy if exists "authenticated tutor names" on public.tutors;
create policy "authenticated tutor names" on public.tutors for select to authenticated using (active = true and deleted_at is null);

drop policy if exists "authenticated availability" on public.availability_slots;
create policy "authenticated availability" on public.availability_slots for select to authenticated using (
  starts_at > now() - interval '1 year'
  and (
    status = 'open'
    or exists (
      select 1 from public.tutor_roles r
      where r.tutor_id = availability_slots.tutor_id
        and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
    )
  )
);

drop policy if exists "tutors insert own availability" on public.availability_slots;
create policy "tutors insert own availability" on public.availability_slots for insert to authenticated
with check (
  availability_slots.status = 'open'
  and availability_slots.starts_at > now()
  and exists (select 1 from pg_timezone_names where name = availability_slots.timezone)
  and exists (select 1 from public.tutor_roles r where r.tutor_id = availability_slots.tutor_id and r.email = lower(coalesce(auth.jwt() ->> 'email', '')))
);

drop policy if exists "tutors update own availability" on public.availability_slots;
create policy "tutors update own availability" on public.availability_slots for update to authenticated
using (availability_slots.status = 'open' and exists (select 1 from public.tutor_roles r where r.tutor_id = availability_slots.tutor_id and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))))
with check (
  availability_slots.status in ('open', 'cancelled')
  and (availability_slots.status = 'cancelled' or availability_slots.starts_at > now())
  and exists (select 1 from pg_timezone_names where name = availability_slots.timezone)
  and exists (select 1 from public.tutor_roles r where r.tutor_id = availability_slots.tutor_id and r.email = lower(coalesce(auth.jwt() ->> 'email', '')))
);

drop policy if exists "requester or assigned tutor history" on public.session_requests;
drop policy if exists "requester history" on public.session_requests;
drop policy if exists "requester or assigned tutor history" on public.session_requests;
create policy "requester or assigned tutor history" on public.session_requests for select to authenticated using (
  requester_user_id = auth.uid() or exists (
    select 1 from public.tutor_roles r where r.tutor_id = session_requests.tutor_id
    and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
  )
);
drop function if exists public.is_assigned_tutor(uuid);

drop policy if exists "tutors read own role" on public.tutor_roles;
create policy "tutors read own role" on public.tutor_roles for select to authenticated
using (email = lower(coalesce(auth.jwt() ->> 'email', '')));

drop policy if exists "tutors update own timezone" on public.tutor_roles;
create policy "tutors update own timezone" on public.tutor_roles for update to authenticated
using (email = lower(coalesce(auth.jwt() ->> 'email', '')))
with check (email = lower(coalesce(auth.jwt() ->> 'email', '')));

create or replace function public.assign_tutor_role(p_tutor_id uuid, p_email text, p_actor_user_id uuid default null)
returns uuid language plpgsql security definer set search_path = public as $$
declare role_id uuid; normalized_email text := lower(trim(p_email));
begin
  if normalized_email = '' then raise exception 'Tutor email is required'; end if;
  if not exists (select 1 from public.tutors where id = p_tutor_id and deleted_at is null) then raise exception 'Tutor not found'; end if;
  delete from public.tutor_roles where email = normalized_email or tutor_id = p_tutor_id;
  update public.tutors set tutor_email = normalized_email where id = p_tutor_id;
  insert into public.tutor_roles(email, tutor_id, assigned_by) values (normalized_email, p_tutor_id, p_actor_user_id) returning id into role_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id, details)
  values ('assigned_tutor_role', 'tutor_role', role_id, p_actor_user_id, jsonb_build_object('tutor_id', p_tutor_id));
  return role_id;
end;
$$;
revoke all on function public.assign_tutor_role(uuid, text, uuid) from public, anon, authenticated;
grant execute on function public.assign_tutor_role(uuid, text, uuid) to service_role;

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
    raise exception 'The guardian email must match the signed-in account';
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
  select * into chosen_tutor from public.tutors where id = p_tutor_id and active = true and deleted_at is null;
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
    guardian_name, guardian_email, requester_user_id, notes, student_timezone, status
  ) values (
    p_tutor_id, p_slot_id, trim(p_student_first_name), p_student_grade,
    p_subject, trim(p_guardian_name), account_email, auth.uid(), coalesce(trim(p_notes), ''), p_student_timezone, 'confirmed'
  ) returning id into request_id;
  update public.availability_slots set status = 'booked' where id = p_slot_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id)
  values ('created_and_auto_confirmed', 'session_request', request_id, auth.uid());
  return request_id;
end;
$$;

create or replace function public.change_session_status(p_request_id uuid, p_status text, p_meeting_url text default null)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  booking public.session_requests%rowtype;
begin
  if p_status not in ('confirmed', 'cancelled', 'completed', 'declined') then raise exception 'Invalid status'; end if;
  if p_meeting_url is not null and p_meeting_url !~ '^https://[^[:space:]]+$' then raise exception 'Invalid lesson link'; end if;
  select * into booking from public.session_requests where id = p_request_id for update;
  if booking.id is null then raise exception 'Request not found'; end if;
  if booking.status = 'requested' and p_status not in ('confirmed', 'cancelled', 'declined') then raise exception 'Invalid status change'; end if;
  if booking.status = 'confirmed' and p_status not in ('confirmed', 'cancelled', 'completed', 'declined') then raise exception 'Invalid status change'; end if;
  if booking.status in ('cancelled', 'completed', 'declined') then raise exception 'This request is already closed'; end if;
  if p_status = 'confirmed' and coalesce(trim(p_meeting_url), '') = '' then raise exception 'A lesson link is required before confirming'; end if;
  update public.session_requests set status = p_status, meeting_url = case when p_status = 'confirmed' then p_meeting_url else meeting_url end, updated_at = now() where id = p_request_id;
  update public.availability_slots set status = case
    when p_status = 'confirmed' then 'booked'
    when p_status in ('cancelled', 'declined') and starts_at > now() then 'open'
    when p_status in ('cancelled', 'declined') then 'cancelled'
    else status end
  where id = booking.slot_id;
  insert into public.audit_log(action, record_type, record_id, details)
  values (p_status, 'session_request', p_request_id, jsonb_build_object('meeting_url_added', p_status = 'confirmed'));
  return p_request_id;
end;
$$;

create or replace function public.cancel_my_session(p_request_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  booking public.session_requests%rowtype;
  lesson_start timestamptz;
begin
  if auth.uid() is null then raise exception 'Authentication required'; end if;
  select * into booking
  from public.session_requests
  where id = p_request_id and requester_user_id = auth.uid()
  for update;
  if booking.id is null then raise exception 'Request not found'; end if;
  if booking.status not in ('requested', 'confirmed') then raise exception 'This request is already closed'; end if;
  select starts_at into lesson_start from public.availability_slots where id = booking.slot_id for update;
  if lesson_start <= now() then raise exception 'Past or started lessons cannot be cancelled'; end if;
  update public.session_requests set status = 'cancelled', updated_at = now() where id = booking.id;
  update public.availability_slots set status = 'open' where id = booking.slot_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id)
  values ('cancelled_by_student', 'session_request', booking.id, auth.uid());
  return booking.id;
end;
$$;

create or replace function public.decline_my_tutoring_session(p_request_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  booking public.session_requests%rowtype;
  lesson_start timestamptz;
  account_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
begin
  if auth.uid() is null or account_email = '' then raise exception 'Authentication required'; end if;
  select sr.* into booking
  from public.session_requests sr
  join public.tutor_roles role on role.tutor_id = sr.tutor_id and role.email = account_email
  where sr.id = p_request_id
  for update of sr;
  if booking.id is null then raise exception 'Request not found or tutor access denied'; end if;
  if booking.status not in ('requested', 'confirmed') then raise exception 'This request is already closed'; end if;
  select starts_at into lesson_start from public.availability_slots where id = booking.slot_id for update;
  if lesson_start <= now() then raise exception 'Past or started lessons cannot be declined'; end if;
  update public.session_requests set status = 'declined', updated_at = now() where id = booking.id;
  update public.availability_slots set status = 'open' where id = booking.slot_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id)
  values ('declined_by_tutor', 'session_request', booking.id, auth.uid());
  return booking.id;
end;
$$;

create or replace function public.delete_tutor_safely(p_tutor_id uuid, p_actor_user_id uuid default null)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_tutor public.tutors%rowtype;
begin
  select * into selected_tutor from public.tutors where id = p_tutor_id for update;
  if selected_tutor.id is null or selected_tutor.deleted_at is not null then raise exception 'Tutor not found'; end if;
  if exists (
    select 1
    from public.session_requests r
    join public.availability_slots s on s.id = r.slot_id
    where r.tutor_id = p_tutor_id
      and r.status in ('requested', 'confirmed')
      and s.ends_at > now()
  ) then
    raise exception 'Tutor has active future bookings';
  end if;
  update public.tutors set active = false, deleted_at = now() where id = p_tutor_id;
  update public.availability_slots set status = 'cancelled'
  where tutor_id = p_tutor_id and status = 'open' and starts_at > now();
  delete from public.tutor_roles where tutor_id = p_tutor_id;
  insert into public.audit_log(action, record_type, record_id, actor_user_id)
  values ('deleted', 'tutor', p_tutor_id, p_actor_user_id);
  return p_tutor_id;
end;
$$;

-- Remove the insecure earlier overload that accepted a caller-supplied user id.
drop function if exists public.request_tutoring_session(uuid, uuid, text, text, smallint, text, text, text, text, uuid);
drop function if exists public.request_tutoring_session(uuid, uuid, text, text, smallint, text, text, text, text);
drop function if exists public.approve_tutor_application(uuid);

revoke all on function public.request_tutoring_session(uuid, uuid, text, smallint, text, text, text, text, text) from public, anon;
grant execute on function public.request_tutoring_session(uuid, uuid, text, smallint, text, text, text, text, text) to authenticated;
revoke all on function public.change_session_status(uuid, text, text) from public, anon, authenticated;
grant execute on function public.change_session_status(uuid, text, text) to service_role;
revoke all on function public.cancel_my_session(uuid) from public, anon;
grant execute on function public.cancel_my_session(uuid) to authenticated;
revoke all on function public.decline_my_tutoring_session(uuid) from public, anon;
grant execute on function public.decline_my_tutoring_session(uuid) to authenticated;
revoke all on function public.delete_tutor_safely(uuid, uuid) from public, anon, authenticated;
grant execute on function public.delete_tutor_safely(uuid, uuid) to service_role;

-- Legacy tutor_applications/tutor-cvs data, if present, is intentionally left untouched.
-- It is no longer read by the app and remains inaccessible under its existing RLS.

commit;
