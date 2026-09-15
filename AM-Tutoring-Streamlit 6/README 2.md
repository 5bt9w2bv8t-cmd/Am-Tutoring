# AM Tutoring — Streamlit production plan

This folder is a complete Streamlit-ready replacement for the prototype. It includes the public student journey, Supabase email accounts, an owner dashboard restricted to `taleealali5@gmail.com`, recurring availability generation, collision-safe dated slots, personal booking history, and email notifications. Tutor recruitment is intentionally email-only: the site tells interested students to email `taleealali5@gmail.com` instead of collecting an application form.

## The correct setup

- **Website:** Streamlit Community Cloud
- **Permanent database:** Supabase Postgres
- **Private CV files:** a private Supabase Storage bucket
- **Transactional email:** Resend
- **Source hosting:** a private GitHub repository connected to Streamlit
- **Owner account and inbox:** `taleealali5@gmail.com`

Do not use a local SQLite file as the production database. A hosted Streamlit app can restart or be replaced, so local files are not the authoritative place for applications, bookings, or CVs.

## What was wrong or incomplete in the prototype

1. Email delivery was prepared but not connected to a real sender. An inbox address cannot authorize a website to send mail.
2. The live site and its database were private to the owner, so real students and tutors could not access it.
3. Availability was free text. The finished flow lets the owner choose weekdays, an hour range, lesson length, break length, timezone, and number of weeks; it then generates real dated slots automatically.
4. There was no delivery log showing whether each email succeeded or failed.
5. Application approval did not notify the applicant and guardian automatically.
6. Booking confirmation, cancellation, rejection, and completion did not notify every relevant person.
7. There was no meeting-link step before confirming a session.
8. The owner area now uses Supabase email accounts. The configured owner email gets management tools; guardians and tutors see only their own history and status.
9. If CVs are ever reintroduced, they need private storage, size/type checks, short-lived review links, and a rule telling minors not to include addresses or identification numbers.
10. A tutoring service for minors needs guardian-led contact, minimal student data, an audit trail, a privacy notice, safeguarding rules, and a clear deletion/retention process.

## Database design

| Table | Purpose |
|---|---|
| `tutor_applications` | Legacy table retained only if structured applications are reopened later |
| `tutors` | Approved tutor profile plus private contact fields used only by the server |
| `availability_slots` | Real dated start/end times with open, requested, booked, or cancelled status |
| `session_requests` | Student/guardian request, selected tutor and slot, status, and lesson link |
| `email_events` | Every attempted notification, provider ID, success/failure, and error |
| `audit_log` | Owner approvals and booking changes |

The database functions in `schema.sql` perform approval and booking changes atomically. The unique active-request index plus row locking stops double booking. Row Level Security is enabled and browser roles receive no table access; the Streamlit server uses a secret server key.

## Who receives each email

| Event | Owner/business inbox | Tutor email | Tutor guardian | Student guardian |
|---|---:|---:|---:|---:|
| Tutor recruitment | — | Email the owner directly | — | — |
| Tutor approved/rejected | Copy | Decision | — | — |
| Available time published | Copy | Notice | — | — |
| Session requested | Copy | Request | — | Receipt |
| Session confirmed + link | Copy | Confirmation | — | Confirmation |
| Session cancelled/declined | Copy | Update | — | Update |
| Session completed | Copy | Update | — | Update |

Emails are separate messages so recipients do not see one another’s addresses. No student email or phone number is collected.

## Setup steps

1. Create a Supabase project.
2. Open its SQL Editor, paste all of `schema.sql`, and run it once.
3. Create a Resend account, verify a sending domain, and create an API key.
4. In Supabase Authentication, enable email/password sign-in and decide whether new accounts must confirm their email.
5. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` for local testing. Replace every placeholder. Never commit that secrets file.
6. Put this folder in a private GitHub repository.
7. In Streamlit Community Cloud, create an app using `app.py` as the entrypoint.
8. Paste the same secret values into Streamlit’s **Advanced settings → Secrets**.
9. Create the owner account using `taleealali5@gmail.com`; it is automatically recognized as the only owner.
10. Test with fake information first: generate recurring tutor times, request one, confirm it, and verify every inbox and database record.
11. Add the privacy, safeguarding, cancellation, and data-deletion policies before opening the app to real minors.

Run locally with:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Required production policies

- Collect only the student’s first name, country, grade, subject, and guardian contact.
- Never display tutor or guardian email addresses publicly.
- Do not permit direct private minor-to-minor messaging.
- Require owner approval before publishing a tutor profile that was arranged by email.
- Require a guardian to receive all booking and status emails.
- Use owner-controlled meeting links and do not publish them.
- Define who supervises sessions and how concerns are reported.
- Set a retention period for owner email correspondence and any future CVs.
- Let a guardian request correction or deletion of their data.
- Keep an incident log separate from public profiles.
- Protect the owner’s email account with a strong unique password and two-factor authentication.
