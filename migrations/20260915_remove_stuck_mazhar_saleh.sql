-- One-time cleanup requested for the stuck Mazhar Saleh reservation.
begin;

update public.availability_slots as slot
set status = case when slot.starts_at > now() then 'open' else 'cancelled' end
where slot.id in (
  select request.slot_id
  from public.session_requests as request
  where lower(trim(request.student_first_name)) = 'mazhar saleh'
);

delete from public.session_requests
where lower(trim(student_first_name)) = 'mazhar saleh';

commit;
