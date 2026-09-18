-- Allow tutors from every country and tutors of any valid age.
alter table public.tutors drop constraint if exists tutors_country_check;
alter table public.tutors drop constraint if exists tutors_age_check;
alter table public.tutors drop constraint if exists tutors_age_valid_check;
alter table public.tutors
  add constraint tutors_age_valid_check check (age between 1 and 120);
