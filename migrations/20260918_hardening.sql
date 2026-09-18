-- ClassMatch security hardening for authenticated availability reads.
-- Students can see only open future times; assigned tutors can see their own
-- booked, requested, cancelled, and completed history.
drop policy if exists "authenticated availability" on public.availability_slots;
create policy "authenticated availability" on public.availability_slots
for select to authenticated using (
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
create policy "tutors insert own availability" on public.availability_slots
for insert to authenticated with check (
  availability_slots.status = 'open'
  and availability_slots.starts_at > now()
  and exists (select 1 from pg_timezone_names where name = availability_slots.timezone)
  and exists (
    select 1 from public.tutor_roles r
    where r.tutor_id = availability_slots.tutor_id
      and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
  )
);

drop policy if exists "tutors update own availability" on public.availability_slots;
create policy "tutors update own availability" on public.availability_slots
for update to authenticated
using (
  availability_slots.status = 'open'
  and exists (
    select 1 from public.tutor_roles r
    where r.tutor_id = availability_slots.tutor_id
      and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
  )
)
with check (
  availability_slots.status in ('open', 'cancelled')
  and (availability_slots.status = 'cancelled' or availability_slots.starts_at > now())
  and exists (select 1 from pg_timezone_names where name = availability_slots.timezone)
  and exists (
    select 1 from public.tutor_roles r
    where r.tutor_id = availability_slots.tutor_id
      and r.email = lower(coalesce(auth.jwt() ->> 'email', ''))
  )
);
