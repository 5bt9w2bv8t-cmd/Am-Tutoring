# TM Tutoring

A production-ready Streamlit application for free online tutoring worldwide. Families can match by grade and subject, request collision-safe dated slots, receive email updates, and track status. Owners assign verified tutor accounts; approved tutors of any age manage their own timezone, availability, and schedule.

## Architecture

- `app.py` — Streamlit pages and forms
- `auth.py` — Supabase email/password sessions and password recovery
- `backend.py` — database operations and owner authorization boundary
- `core.py` — validated, testable scheduling and formatting rules
- `mailer.py` — separate Resend notifications and delivery logging
- `schema.sql` — PostgreSQL tables, indexes, atomic booking functions, grants, and RLS
- `assets/style.css` — responsive visual system
- `tests/` — unit and Streamlit smoke tests

Tutor recruitment is intentionally email-only. No tutor application or CV is uploaded through the site.

## Production setup

1. Create a Supabase project. In **SQL Editor**, run all of `schema.sql`. It is safe to rerun on an existing TM Tutoring database.
2. In **Authentication → Providers → Email**, enable email/password sign-in and turn **Confirm email** on. The app deliberately refuses unverified sessions.
3. For the in-app reset-code flow, edit Supabase’s **Reset Password** email template so it displays `{{ .Token }}` as the reset code. Do not use only the confirmation link.
4. Create a Resend account, verify a sending domain, and create an API key.
5. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, replace every placeholder, and generate a unique 32+ character `COOKIE_PASSWORD`. Never commit this file.
6. Create owner accounts with `taleenalali5@gmail.com` and `mazharysaleh@gmail.com`. Both receive access to the owner dashboard.
7. Deploy the GitHub repository on Streamlit Community Cloud with `app.py` as the entrypoint. Copy the same secret values into **App settings → Secrets**.
8. Add a tutor, assign their verified account under **Owner dashboard → Tutor access**, create test availability, request a session from a separate student account, then verify both dashboards and inboxes before launch.

The service-role key is server-only. It belongs only in Streamlit secrets, never in source code, browser code, screenshots, or a public repository. The anon key is designed to be public, but RLS still limits it.

## Data and safety

- Public tutor results exclude emails and other private fields.
- Booking creation runs as the signed-in user. The database derives the user ID from the verified JWT instead of trusting browser input.
- RLS lets each student see only their reservations and each assigned tutor see only their own lessons and availability.
- Slot locking and a partial unique index stop double bookings.
- Owner-only changes use the server key only after the signed-in email is checked again in the business layer.
- Every email is sent separately so recipients do not see one another’s address.
- Collect only the student’s first name, grade, subject, account email, timezone, and brief learning notes.

The public site includes a concise privacy and safeguarding notice. Before serving real minors, the school should have its final wording reviewed for local legal and school-policy requirements. Protect the owner inbox and Supabase account with two-factor authentication.

## Local run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```
