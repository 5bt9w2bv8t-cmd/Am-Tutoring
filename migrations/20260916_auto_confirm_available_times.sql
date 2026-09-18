-- Automatically confirm lessons booked from tutor-created availability.
begin;

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
  select * into chosen_tutor
  from public.tutors
  where id = p_tutor_id and active = true and deleted_at is null;
  if chosen_tutor.id is null
     or p_student_grade not between chosen_tutor.min_student_grade and chosen_tutor.max_student_grade
     or not (p_subject = any(chosen_tutor.subjects)) then
    raise exception 'Tutor does not match this request';
  end if;
  select * into chosen_slot
  from public.availability_slots
  where id = p_slot_id and tutor_id = p_tutor_id
  for update;
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
  update public.session_requests
  set status = p_status,
      meeting_url = case when p_status = 'confirmed' then p_meeting_url else meeting_url end,
      updated_at = now()
  where id = p_request_id;
  update public.availability_slots
  set status = case
    when p_status = 'confirmed' then 'booked'
    when p_status in ('cancelled', 'declined') and starts_at > now() then 'open'
    when p_status in ('cancelled', 'declined') then 'cancelled'
    else status
  end
  where id = booking.slot_id;
  insert into public.audit_log(action, record_type, record_id, details)
  values (p_status, 'session_request', p_request_id, jsonb_build_object('meeting_url_added', p_status = 'confirmed'));
  return p_request_id;
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

revoke all on function public.request_tutoring_session(uuid, uuid, text, smallint, text, text, text, text, text) from public, anon;
grant execute on function public.request_tutoring_session(uuid, uuid, text, smallint, text, text, text, text, text) to authenticated;
revoke all on function public.change_session_status(uuid, text, text) from public, anon, authenticated;
grant execute on function public.change_session_status(uuid, text, text) to service_role;
revoke all on function public.decline_my_tutoring_session(uuid) from public, anon;
grant execute on function public.decline_my_tutoring_session(uuid) to authenticated;

commit;
