# AM Tutoring

A production-ready Streamlit application for free, student-led tutoring in Syria and the UAE. Families can match with approved tutors, request collision-safe dated slots, receive email updates, and track status. The owner can manage tutors, generate recurring availability, and confirm or close requests.

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

1. Create a Supabase project. In **SQL Editor**, run all of `schema.sql`.
2. In **Authentication → Providers → Email**, enable email/password sign-in. Keeping email confirmation enabled is recommended.
3. For the in-app reset-code flow, edit Supabase’s **Reset Password** email template so it displays `{{ .Token }}` as the reset code. Do not use only the confirmation link.
4. Create a Resend account, verify a sending domain, and create an API key.
5. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace every placeholder for local use. Never commit this file.
6. Create owner accounts with `taleenalali5@gmail.com` and `mazharysaleh@gmail.com`. Both receive the owner dashboard and operational notifications.
7. Deploy the GitHub repository on Streamlit Community Cloud with `app.py` as the entrypoint. Copy the same secret values into **App settings → Secrets**.
8. Add a tutor, generate test availability, create a separate guardian account, request a session, then confirm it and verify all inboxes before launch.

The service-role key is server-only. It belongs only in Streamlit secrets, never in source code, browser code, screenshots, or a public repository. The anon key is designed to be public, but RLS still limits it.

## Data and safety

- Public tutor results exclude emails and other private fields.
- Booking creation runs as the signed-in user. The database derives the user ID from the verified JWT instead of trusting browser input.
- RLS lets a guardian see only their requests and lets a tutor see only requests assigned to their email.
- Slot locking and a partial unique index stop double bookings.
- Owner-only changes use the server key only after the signed-in email is checked again in the business layer.
- Every email is sent separately so recipients do not see one another’s address.
- Collect only the student’s first name, country, grade, subject, guardian name/email, and brief learning notes.

Before serving real minors, the school should publish privacy, safeguarding, cancellation, supervision, incident-reporting, and data-retention policies. Protect the owner inbox and Supabase account with two-factor authentication.

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
