from __future__ import annotations

from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import streamlit as st
from email_validator import EmailNotValidError, validate_email

from auth import access_token, current_user, is_owner, reset_password_with_code, send_password_code, sign_in, sign_out, sign_up
from backend import add_recurring_slots, add_tutor, all_session_requests, approved_tutors, assign_tutor_role, cancel_open_slot, change_session_status, configuration_missing, delete_tutor, friendly_error, managed_tutors, open_slot_summaries, open_slots, public_tutors, remove_tutor_role, request_session, tutor_add_recurring_slots, tutor_assignment, tutor_cancel_open_slot, tutor_role_assignments, tutor_session_requests, tutor_set_timezone, tutor_slots, tutor_update_open_slot, upcoming_slots, update_tutor, user_session_requests
from core import COUNTRIES, GRADES, LANGUAGES, SUBJECTS, TIMEZONES, WEEKDAYS, format_slot, valid_meeting_url
from mailer import notify_session_request, notify_session_status


st.set_page_config(page_title="TM Tutoring", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")
style_path = Path(__file__).with_name("assets") / "style.css"
try:
    stylesheet = style_path.read_text(encoding="utf-8")
except FileNotFoundError:
    # The app remains usable if a deployment omitted the optional styling asset.
    stylesheet = ".stApp { background: #f7f4ed; }"
st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)


def go(page: str) -> None:
    st.session_state.page = page


def flash(kind: str, message: str) -> None:
    st.session_state.flash = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop("flash", None)
    if item:
        getattr(st, item[0])(item[1])


def normal_email(value: str) -> str:
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError("Enter a valid email address.") from exc


def related_record(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def home(user: dict | None) -> None:
    st.markdown('<div class="home-page-marker" aria-hidden="true"></div><header class="site-header"><a class="brand" href="#top"><span class="brand-mark">TM</span><span>TM Tutoring</span></a><nav><a href="#about">About</a><a href="#safety">Help &amp; Safety</a></nav></header><div id="top"></div>', unsafe_allow_html=True)
    st.markdown('<section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="live-dot"></span> Student-led · Online · Free</div><h1>Students helping<br>students <em>grow.</em></h1><p class="hero-lede">TM Tutoring connects school students in Syria and the UAE with approved student tutors for friendly, free online support.</p></div><div class="hero-board" aria-label="How TM Tutoring works"><div class="tape tape-one"></div><div class="tape tape-two"></div><div class="board-note note-yellow"><span class="note-kicker">STUDENT</span><strong>Choose what<br>you need.</strong><span class="scribble">〰</span></div><div class="board-note note-white"><div class="mini-avatar">TM</div><div><span class="note-kicker">A GOOD MATCH</span><strong>Pick a tutor + time</strong><small>Send a guardian-led request</small></div><span class="play">→</span></div><div class="board-note note-blue"><span class="star">✦</span><strong>Learn.<br>Help.<br>Grow.</strong><small>تعلم • ساعد • انمو</small></div><div class="pencil-line"></div></div></section>', unsafe_allow_html=True)
    if st.button("Find a free tutor  →", type="primary", key="hero_find"):
        go("Find a tutor")
        st.rerun()
    gmail_url = "https://mail.google.com/mail/?" + urlencode({"view": "cm", "fs": "1", "to": "taleenalali5@gmail.com", "su": "TM Tutoring volunteer", "body": "Hello,\n\nI’m interested in volunteering as a student tutor with TM Tutoring.\n\nName:\nAge:\nGrade:\nCountry:\nSubjects:\nLanguages:\nAvailable times:\n\nI will attach my CV to this email.\n\nThank you."})
    st.markdown(f'<div class="micro-proof"><span>✓</span> Always free &nbsp; <span>✓</span> Guardian-approved &nbsp; <span>✓</span> Arabic &amp; English</div><div class="ticker"><span>LEARN TOGETHER</span><b>✦</b><span>SHARE WHAT YOU KNOW</span><b>✦</b><span>GROW WITH TM TUTORING</span></div><section class="start-band"><div><span>Start here</span><h2>Find the right tutor in five simple steps.</h2><p>Choose the student’s grade and subject, then select an approved tutor and available time.</p></div></section><section class="about section" id="about"><div class="section-label">WHAT TM TUTORING DOES</div><div class="about-grid"><h2>A simple way for students to help each other.</h2><div class="about-copy"><p>Families find support by grade and subject. Approved student tutors share the subjects and times they can offer.</p><p>Every session request is managed through a guardian, giving students a welcoming way to learn and volunteer safely.</p></div></div><div class="impact-row"><div><strong>100%</strong><span>Free for families</span></div><div><strong>13–18</strong><span>Student tutor ages</span></div><div><strong>2</strong><span>Countries connected</span></div><div><strong>1:1</strong><span>Focused support</span></div></div></section><section class="how section"><div class="section-label">HOW IT WORKS</div><div class="section-heading-row"><h2>Small steps.<br>Real progress.</h2><p>Everything is designed to make finding help feel clear, friendly, and safe.</p></div><div class="steps"><article><div class="step-icon">⌕</div><h3>Choose what you need</h3><p>Select a grade and subject to see suitable tutors.</p></article><article><div class="step-icon">→</div><h3>Pick a tutor + time</h3><p>Compare approved student profiles and open lesson times.</p></article><article><div class="step-icon">✦</div><h3>Learn, help, grow</h3><p>A guardian requests the session and receives every update.</p></article></div></section><section class="safety section" id="safety"><div class="safety-card"><div class="safety-graphic"><span>✓</span><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div></div><div><div class="section-label">STUDENT SAFETY</div><h2>Guardians stay in the loop.</h2><p>Every session request is managed through a guardian. Tutor profiles are reviewed before they appear, and no private contact details are displayed.</p><ul><li><span>✓</span> Tutor profiles require owner approval</li><li><span>✓</span> Guardians receive session communication</li><li><span>✓</span> No private student contact is displayed</li></ul></div></div></section><section class="tutor-contact"><div><span>STUDENT VOLUNTEERS</span><h2>Want to tutor?</h2><p>Email your CV, age, grade, subjects, languages, and available times to the TM Tutoring manager. Student tutors must be ages 13–18.</p></div><div class="tutor-contact-action"><a class="button button-light" href="{escape(gmail_url, quote=True)}" target="_blank" rel="noopener noreferrer">Email about tutoring <span>↗</span></a><small>taleenalali5@gmail.com</small></div></section><footer><a class="brand" href="#top"><span class="brand-mark">TM</span><span>TM Tutoring</span></a><p>Students helping students in Syria and the UAE.</p><small>© 2026 TM Tutoring. Free, student-led learning.</small></footer>', unsafe_allow_html=True)


def clear_reservation(*, keep_search: bool = True) -> None:
    keys = (
        "reservation_tutor", "reservation_step", "reservation_date", "reservation_slot_id",
        "reservation_selected_date", "reservation_selected_slot_id",
        "reservation_confirmation", "reservation_draft", "booking_submitting",
        "booking_student_name", "booking_guardian_name", "booking_notes", "booking_consent",
    )
    for key in keys:
        st.session_state.pop(key, None)
    if not keep_search:
        for key in ("search", "matches", "search_grade", "search_subject", "student_timezone"):
            st.session_state.pop(key, None)


def reservation_progress(step: int) -> None:
    labels = ("Tutor & time", "Your details", "Review", "Confirmation")
    parts = []
    for index, label in enumerate(labels, 1):
        state = "complete" if index < step else "active" if index == step else ""
        parts.append(f'<span class="{state}">{index} · {label}</span>')
    st.markdown(f'<div class="reservation-progress">{"".join(parts)}</div>', unsafe_allow_html=True)


def find_tutor(user: dict | None) -> None:
    st.markdown('<div class="app-page-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown('<h1 class="inner-page-title">Find a tutor</h1>', unsafe_allow_html=True)
    st.caption("Tell us what the student needs, compare matching tutors, then reserve a real open lesson time.")

    search = st.session_state.get("search")
    if not search:
        st.markdown('<p class="area-kicker">STEP 1 · LEARNING NEEDS</p>', unsafe_allow_html=True)
        with st.form("tutor_search", clear_on_submit=False):
            filters = st.columns(2)
            grade = filters[0].selectbox("Student grade", GRADES, format_func=lambda item: f"Grade {item}", key="search_grade")
            subject = filters[1].selectbox("Subject", SUBJECTS, key="search_subject")
            find = st.form_submit_button("Find matching tutors  →", type="primary", use_container_width=True)
        if not find:
            st.info("Choose the student grade and subject to begin.")
            return
        try:
            with st.spinner("Finding approved tutors…"):
                tutors = public_tutors(grade, subject)
            st.session_state.search = {"grade": grade, "subject": subject}
            st.session_state.matches = tutors
            clear_reservation(keep_search=True)
            st.rerun()
        except Exception as exc:
            st.error(friendly_error(exc))
            return

    search = st.session_state["search"]
    grade, subject = search["grade"], search["subject"]
    st.markdown(
        f'<div class="filter-summary"><div><small>GRADE</small><strong>Grade {grade}</strong></div>'
        f'<div><small>SUBJECT</small><strong>{escape(subject)}</strong></div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Change search filters", key="change_filters"):
        clear_reservation(keep_search=False)
        st.rerun()

    try:
        with st.spinner("Updating tutor availability…"):
            tutors = public_tutors(grade, subject)
            summaries = open_slot_summaries(tuple(str(item["id"]) for item in tutors))
        st.session_state.matches = tutors
    except Exception as exc:
        st.error(friendly_error(exc))
        return
    if not tutors:
        st.markdown('<div class="empty-state"><span>⌕</span><h3>No matching tutors yet</h3><p>Try another subject or grade. Only approved tutors matching every selected filter appear here.</p></div>', unsafe_allow_html=True)
        return

    selected_id = st.session_state.get("reservation_tutor")
    tutor = next((item for item in tutors if str(item["id"]) == str(selected_id)), None)
    if selected_id and tutor is None:
        clear_reservation(keep_search=True)
        st.warning("That tutor is no longer available. Please choose another tutor below.")
        selected_id = None

    if not selected_id:
        st.markdown('<p class="area-kicker results-kicker">STEP 2 · MATCHING TUTORS</p>', unsafe_allow_html=True)
        st.subheader(f"{len(tutors)} matching tutor{'s' if len(tutors) != 1 else ''}")
        for offset in range(0, len(tutors), 2):
            columns = st.columns(2)
            for column, item in zip(columns, tutors[offset:offset + 2]):
                summary = summaries.get(str(item["id"]), {"count": 0})
                chips = "".join(f'<span>{escape(str(value))}</span>' for value in item["subjects"])
                availability = format_slot(summary["next_slot"]) if summary.get("next_slot") else "No upcoming availability yet"
                with column:
                    with st.container(border=True):
                        st.markdown(
                            f'<article class="tutor-profile tutor-profile-flat"><div class="tutor-avatar">{escape(item["full_name"][:1].upper())}</div>'
                            f'<div class="tutor-profile-copy"><p class="profile-kicker">APPROVED STUDENT TUTOR</p>'
                            f'<h2>{escape(item["full_name"])}</h2><p>{escape(item["bio"])}</p><div class="profile-chips">{chips}</div>'
                            f'<small>Grade {item["school_grade"]} · Teaches grades {item["min_student_grade"]}–{item["max_student_grade"]}<br>{escape(", ".join(item["languages"]))}</small>'
                            f'<div class="next-slot"><b>{summary["count"]} open time{"s" if summary["count"] != 1 else ""}</b><span>{escape(availability)}</span></div></div></article>',
                            unsafe_allow_html=True,
                        )
                        choose = st.button("Choose this tutor  →" if summary["count"] else "No times available", key=f"choose_{item['id']}", type="primary", disabled=not summary["count"], use_container_width=True)
                        if choose:
                            clear_reservation(keep_search=True)
                            st.session_state.reservation_tutor = str(item["id"])
                            st.session_state.reservation_step = 1
                            st.rerun()
        return

    assert tutor is not None
    if st.session_state.get("reservation_step") == 4 and st.session_state.get("reservation_confirmation"):
        booking, emailed = st.session_state.reservation_confirmation
        reservation_progress(4)
        st.markdown('<div class="confirmation-mark">✓</div><p class="area-kicker confirmation-kicker">REQUEST SAVED</p><h2 class="confirmation-title">Your reservation is in.</h2>', unsafe_allow_html=True)
        st.success("Email confirmations were sent." if emailed else "Your reservation is saved. Email delivery could not be confirmed, but no duplicate booking was created.")
        st.markdown(
            f'<div class="reservation-summary confirmation-summary"><b>Waiting for owner confirmation</b>'
            f'<span>Tutor · {escape(tutor["full_name"])}</span><span>{escape(subject)} · Grade {grade}</span>'
            f'<span>{escape(format_slot(booking["availability_slots"], booking.get("student_timezone") or "UTC"))}</span></div>', unsafe_allow_html=True,
        )
        st.caption("The lesson appears in My account. You will receive another email when it is confirmed or updated.")
        actions = st.columns(2)
        if actions[0].button("View my reservations", type="primary", use_container_width=True):
            go("My account")
            st.rerun()
        if actions[1].button("Find another tutor", use_container_width=True):
            clear_reservation(keep_search=False)
            st.rerun()
        return

    st.markdown(
        f'<div class="selected-tutor"><div class="tutor-avatar small">{escape(tutor["full_name"][:1].upper())}</div>'
        f'<div><small>YOUR SELECTED TUTOR</small><strong>{escape(tutor["full_name"])}</strong><span>{escape(subject)} · Grades {tutor["min_student_grade"]}–{tutor["max_student_grade"]} · {escape(", ".join(tutor["languages"]))}</span></div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Change tutor", key="change_tutor"):
        clear_reservation(keep_search=True)
        st.rerun()
    if not user:
        st.warning("Sign in before choosing a time so your reservation history can be saved securely.")
        if st.button("Sign in to continue", type="primary"):
            st.session_state.return_page_after_auth = "Find a tutor"
            go("My account")
            st.rerun()
        return

    student_timezone = st.selectbox(
        "Your timezone",
        TIMEZONES,
        index=TIMEZONES.index(st.session_state.get("student_timezone", "Asia/Dubai")) if st.session_state.get("student_timezone", "Asia/Dubai") in TIMEZONES else 0,
        key="student_timezone",
        help="All lesson dates and times below are converted to this timezone.",
    )
    st.caption(f"Every available time is shown in {student_timezone}. Tutor availability is stored securely in UTC.")

    try:
        slots = open_slots(str(tutor["id"]))
    except Exception as exc:
        st.error(friendly_error(exc))
        return
    available = [slot for slot in slots if slot["status"] == "open"]
    unavailable = [slot for slot in slots if slot["status"] != "open"]
    if not available:
        clear_reservation(keep_search=True)
        st.warning("This tutor’s available times were just filled. Choose another tutor or check again later.")
        return

    step = int(st.session_state.get("reservation_step", 1))
    reservation_progress(step)

    def local_date(slot: dict) -> date:
        return datetime.fromisoformat(slot["starts_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(student_timezone)).date()

    dates = sorted({local_date(slot) for slot in available})
    date_keys = [item.isoformat() for item in dates]
    if st.session_state.get("reservation_date") not in date_keys:
        st.session_state.pop("reservation_date", None)
    date_labels = {item.isoformat(): item.strftime("%a, %d %b") for item in dates}

    if step == 1:
        st.subheader("Choose a date and time")
        saved_date = st.session_state.get("reservation_selected_date")
        if saved_date in date_keys and "reservation_date" not in st.session_state:
            st.session_state.reservation_date = saved_date
        chosen_date_key = st.radio("Available dates", date_keys, format_func=date_labels.get, key="reservation_date", horizontal=True)
        day_slots = [slot for slot in available if local_date(slot).isoformat() == chosen_date_key]
        slot_ids = [str(slot["id"]) for slot in day_slots]
        if st.session_state.get("reservation_slot_id") not in slot_ids:
            st.session_state.pop("reservation_slot_id", None)
        saved_slot = st.session_state.get("reservation_selected_slot_id")
        if saved_slot in slot_ids and "reservation_slot_id" not in st.session_state:
            st.session_state.reservation_slot_id = saved_slot
        slot_labels = {
            str(slot["id"]): datetime.fromisoformat(slot["starts_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(student_timezone)).strftime("%H:%M")
            + "–" + datetime.fromisoformat(slot["ends_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(student_timezone)).strftime("%H:%M")
            + f" · {student_timezone}" for slot in day_slots
        }
        slot_id = st.radio("Open lesson times", slot_ids, format_func=slot_labels.get, key="reservation_slot_id", horizontal=True)
        st.caption(f"Times are displayed in your selected timezone: {student_timezone}.")
        if unavailable:
            with st.expander(f"Filled or pending times ({len(unavailable)})"):
                for slot in unavailable:
                    state = "Pending" if slot["status"] == "requested" else "Filled"
                    st.markdown(f'<div class="slot-unavailable"><span>{escape(format_slot(slot, student_timezone))}</span><b>{state}</b></div>', unsafe_allow_html=True)
        selected_slot = next(slot for slot in day_slots if str(slot["id"]) == slot_id)
        st.markdown(f'<div class="reservation-summary"><b>Selected lesson</b><span>{escape(tutor["full_name"])} · {escape(subject)} · Grade {grade}</span><span>{escape(format_slot(selected_slot, student_timezone))}</span></div>', unsafe_allow_html=True)
        if st.button("Continue to student details  →", type="primary", key="continue_details"):
            st.session_state.reservation_selected_date = chosen_date_key
            st.session_state.reservation_selected_slot_id = slot_id
            st.session_state.reservation_step = 2
            st.rerun()
        return

    slot_id = str(st.session_state.get("reservation_selected_slot_id", ""))
    selected_slot = next((slot for slot in available if str(slot["id"]) == slot_id), None)
    if selected_slot is None:
        st.session_state.reservation_step = 1
        st.session_state.pop("reservation_slot_id", None)
        st.session_state.pop("reservation_selected_slot_id", None)
        st.warning("That time is no longer open. Please choose another available time.")
        return

    if step == 2:
        st.markdown(f'<div class="reservation-summary"><b>{escape(tutor["full_name"])}</b><span>{escape(subject)} · Grade {grade}</span><span>{escape(format_slot(selected_slot, student_timezone))}</span></div>', unsafe_allow_html=True)
        draft = st.session_state.get("reservation_draft", {})
        with st.form("session_details", clear_on_submit=False):
            st.subheader("Student and guardian details")
            student_name = st.text_input("Student’s first name only", value=draft.get("student_name", ""), max_chars=50)
            guardian_name = st.text_input("Parent, guardian, or reserver name", value=draft.get("guardian_name", ""), max_chars=100)
            st.text_input("Confirmation email", value=user["email"], disabled=True)
            notes = st.text_area("What does the student need help with?", value=draft.get("notes", ""), max_chars=1000, placeholder="A topic, assignment, or learning goal")
            consent = st.checkbox("I am the parent/guardian or have their permission, and I agree to receive session emails.", value=bool(draft.get("consent", False)))
            continue_review = st.form_submit_button("Review reservation  →", type="primary", use_container_width=True)
        back = st.button("← Back to date and time", key="back_to_time")
        if back:
            st.session_state.reservation_step = 1
            st.rerun()
        if continue_review:
            errors = []
            if not student_name.strip():
                errors.append("Enter the student’s first name.")
            if not guardian_name.strip():
                errors.append("Enter the parent, guardian, or reserver name.")
            if not consent:
                errors.append("Guardian permission and email consent are required.")
            if errors:
                for message in errors:
                    st.error(message)
            else:
                st.session_state.reservation_draft = {"student_name": student_name.strip(), "guardian_name": guardian_name.strip(), "notes": notes.strip(), "consent": consent}
                st.session_state.reservation_step = 3
                st.rerun()
        return

    draft = st.session_state.get("reservation_draft")
    if not draft:
        st.session_state.reservation_step = 2
        st.rerun()
    st.subheader("Review your reservation")
    st.markdown(
        f'<div class="review-card"><div><small>TUTOR</small><strong>{escape(tutor["full_name"])}</strong></div>'
        f'<div><small>SUBJECT</small><strong>{escape(subject)} · Grade {grade}</strong></div>'
        f'<div><small>DATE &amp; TIME</small><strong>{escape(format_slot(selected_slot, student_timezone))}</strong></div>'
        f'<div><small>STUDENT</small><strong>{escape(draft["student_name"])}</strong></div>'
        f'<div><small>GUARDIAN / RESERVER</small><strong>{escape(draft["guardian_name"])}</strong></div>'
        f'<div><small>CONFIRMATION EMAIL</small><strong>{escape(user["email"])}</strong></div>'
        f'<div class="review-wide"><small>LEARNING NOTES</small><strong>{escape(draft.get("notes") or "No additional notes")}</strong></div></div>', unsafe_allow_html=True,
    )
    actions = st.columns(3)
    if actions[0].button("← Change time", key="edit_time", use_container_width=True, disabled=bool(st.session_state.get("booking_submitting"))):
        st.session_state.reservation_step = 1
        st.rerun()
    if actions[1].button("Edit details", key="edit_details", use_container_width=True, disabled=bool(st.session_state.get("booking_submitting"))):
        st.session_state.reservation_step = 2
        st.rerun()
    confirm = actions[2].button("Confirm reservation  →", type="primary", key="confirm_booking", use_container_width=True, disabled=bool(st.session_state.get("booking_submitting")))
    if confirm:
        st.session_state.booking_submitting = True
        st.rerun()
    if st.session_state.get("booking_submitting"):
        try:
            with st.spinner("Securing the lesson time and saving your reservation…"):
                booking = request_session({"p_tutor_id": str(tutor["id"]), "p_slot_id": slot_id, "p_student_first_name": draft["student_name"], "p_student_grade": grade, "p_subject": subject, "p_guardian_name": draft["guardian_name"], "p_guardian_email": user["email"], "p_student_timezone": student_timezone, "p_notes": draft.get("notes", "")}, access_token())
                emailed = notify_session_request(booking)
            st.session_state.reservation_confirmation = (booking, emailed)
            st.session_state.reservation_step = 4
            st.session_state.booking_submitting = False
            st.rerun()
        except Exception as exc:
            message = friendly_error(exc)
            st.session_state.booking_submitting = False
            open_slots.clear()
            if "time" in message.lower() and "taken" in message.lower():
                st.session_state.reservation_step = 1
                st.session_state.pop("reservation_slot_id", None)
                st.session_state.pop("reservation_selected_slot_id", None)
                flash("error", message)
                st.rerun()
            st.error(message)
def account(user: dict | None) -> None:
    st.markdown('<div class="app-page-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown('<h1 class="inner-page-title">My account</h1>', unsafe_allow_html=True)
    st.markdown('<p class="area-kicker">YOUR TM TUTORING</p>', unsafe_allow_html=True)
    st.caption("Sign in to request lessons and keep every reservation detail in one place.")
    if not user:
        sign_in_tab, create_tab, reset_tab = st.tabs(("Sign in", "Create account", "Reset password"))
        with sign_in_tab, st.form("sign_in"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Sign in", type="primary"):
                try:
                    sign_in(normal_email(email), password)
                    go(st.session_state.pop("return_page_after_auth", "My account"))
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))
        with create_tab:
            with st.form("create_account"):
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Create password", type="password", key="signup_password", help="Use at least 8 characters.")
                confirm = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create account", type="primary"):
                    try:
                        if len(password) < 8 or password != confirm:
                            raise ValueError("Use at least 8 characters and make both passwords match.")
                        sign_up(normal_email(email), password)
                        st.success(f"Account created. We sent a verification link to {normal_email(email)}. Open it, then return here to sign in.")
                    except Exception as exc:
                        st.error(friendly_error(exc))
        with reset_tab:
            with st.form("send_reset"):
                email = st.text_input("Account email", key="reset_email")
                if st.form_submit_button("Send reset code"):
                    try:
                        send_password_code(normal_email(email))
                        st.success("If that account exists, Supabase has sent a reset code.")
                    except Exception:
                        st.success("If that account exists, Supabase has sent a reset code.")
            with st.form("finish_reset"):
                email = st.text_input("Account email", key="finish_email")
                code = st.text_input("Reset code", max_chars=12)
                password = st.text_input("New password", type="password", key="reset_password")
                confirm = st.text_input("Confirm new password", type="password", key="reset_confirm")
                if st.form_submit_button("Change password", type="primary"):
                    try:
                        if len(password) < 8 or password != confirm:
                            raise ValueError("Use at least 8 characters and make both passwords match.")
                        reset_password_with_code(normal_email(email), code, password)
                        st.success("Password changed. You can now sign in.")
                    except Exception as exc:
                        st.error(friendly_error(exc))
        return
    left, right = st.columns((4, 1))
    left.write(f"Signed in as **{user['email']}**")
    if right.button("Sign out", use_container_width=True):
        sign_out()
        go("Home")
        st.rerun()
    try:
        rows = user_session_requests(access_token(), user["id"])
    except Exception as exc:
        st.error(friendly_error(exc))
        return
    st.subheader("Upcoming reservations")
    st.caption("Active lessons and future cancellations appear here until their scheduled time passes.")
    if not rows:
        st.info("No upcoming reservations.")
    for item in rows:
        tutor_info = related_record(item.get("tutors"))
        slot_info = related_record(item.get("availability_slots"))
        tutor_name = tutor_info.get("full_name") or "Tutor unavailable"
        with st.container(border=True):
            st.markdown(f'<span class="reservation-status status-{item["status"]}">{item["status"].upper()}</span>', unsafe_allow_html=True)
            st.subheader(f"{item['subject']} with {tutor_name}")
            st.write(format_slot(slot_info, item.get("student_timezone") or slot_info.get("timezone")) if {"starts_at", "ends_at", "timezone"} <= slot_info.keys() else "Lesson time unavailable")
            st.write(f"Student: {item['student_first_name']}")
            if item.get("meeting_url") and item["status"] == "confirmed":
                st.link_button("Open lesson", item["meeting_url"])


def tutor_dashboard(user: dict | None) -> None:
    st.markdown('<div class="app-page-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown('<h1 class="inner-page-title">Tutor dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="area-kicker">YOUR TEACHING SPACE</p>', unsafe_allow_html=True)
    if not user:
        st.error("Sign in with the verified email assigned by the owner to open this dashboard.")
        if st.button("Go to sign in", type="primary"):
            st.session_state.return_page_after_auth = "Tutor dashboard"
            go("My account")
            st.rerun()
        return
    try:
        assignment = tutor_assignment(user)
    except Exception as exc:
        st.error(friendly_error(exc))
        return
    if not assignment:
        st.error("This verified account has not been assigned to a tutor profile by an owner.")
        return

    tutor = related_record(assignment.get("tutors"))
    timezone_name = assignment.get("timezone") if assignment.get("timezone") in TIMEZONES else "Asia/Damascus"
    st.markdown(
        f'<div class="selected-tutor"><div class="tutor-avatar small">{escape((tutor.get("full_name") or "T")[:1])}</div>'
        f'<div><small>VERIFIED TUTOR ACCOUNT</small><strong>{escape(tutor.get("full_name") or user["email"])}</strong>'
        f'<span>{escape(user["email"])} · {escape(timezone_name)}</span></div></div>', unsafe_allow_html=True,
    )

    settings, availability = st.tabs(("Schedule overview", "Manage availability"))
    with settings:
        try:
            slots = tutor_slots(access_token(), user)
            lessons = tutor_session_requests(access_token(), user)
        except Exception as exc:
            st.error(friendly_error(exc))
            return
        now = datetime.now(ZoneInfo("UTC"))

        def lesson_slot(item: dict) -> dict:
            return related_record(item.get("availability_slots"))

        def is_future(item: dict) -> bool:
            slot = lesson_slot(item)
            try:
                return datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00")) > now
            except (KeyError, TypeError, ValueError):
                return False

        available_slots = [slot for slot in slots if slot.get("status") == "open" and datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00")) > now]
        booked_lessons = [item for item in lessons if item.get("status") in {"requested", "confirmed"} and is_future(item)]
        cancelled_lessons = [item for item in lessons if item.get("status") in {"cancelled", "declined"} and is_future(item)]
        completed_lessons = [item for item in lessons if item.get("status") == "completed"][:50]
        overview_tabs = st.tabs((f"Available ({len(available_slots)})", f"Booked ({len(booked_lessons)})", f"Cancelled ({len(cancelled_lessons)})", f"Completed ({len(completed_lessons)})"))
        with overview_tabs[0]:
            if not available_slots:
                st.info("No future available times. Add availability in the next tab.")
            for slot in available_slots:
                st.markdown(f'<div class="dashboard-item"><span class="reservation-status status-confirmed">AVAILABLE</span><strong>{escape(format_slot(slot, timezone_name))}</strong><small>Displayed in {escape(timezone_name)}</small></div>', unsafe_allow_html=True)

        def show_lessons(rows: list[dict], empty_message: str) -> None:
            if not rows:
                st.info(empty_message)
                return
            for item in rows:
                slot = lesson_slot(item)
                with st.container(border=True):
                    st.markdown(f'<span class="reservation-status status-{escape(str(item["status"]))}">{escape(str(item["status"]).upper())}</span>', unsafe_allow_html=True)
                    st.subheader(f"{item['subject']} · Grade {item['student_grade']}")
                    st.write(f"**Student:** {item['student_first_name']}  \n**Student email:** {item['guardian_email']}  \n**Time:** {format_slot(slot, timezone_name)}  \n**Timezone:** {timezone_name}  \n**Student note:** {item.get('notes') or 'None'}")
                    if item.get("meeting_url") and item.get("status") == "confirmed":
                        st.link_button("Open lesson", item["meeting_url"])

        with overview_tabs[1]:
            show_lessons(booked_lessons, "No upcoming requested or confirmed lessons.")
        with overview_tabs[2]:
            show_lessons(cancelled_lessons, "No future cancelled lessons.")
        with overview_tabs[3]:
            show_lessons(completed_lessons, "No completed lessons yet.")

    with availability:
        st.subheader("Availability timezone")
        chosen_timezone = st.selectbox("Your timezone", TIMEZONES, index=TIMEZONES.index(timezone_name), key="tutor_timezone")
        st.caption("Availability is stored in UTC. You manage it here in this timezone; students see it converted to theirs.")
        if chosen_timezone != timezone_name and st.button("Save timezone", type="primary"):
            try:
                tutor_set_timezone(chosen_timezone, access_token(), user)
                flash("success", f"Tutor timezone changed to {chosen_timezone}.")
                st.rerun()
            except Exception as exc:
                st.error(friendly_error(exc))

        with st.form("tutor_recurring_schedule"):
            st.subheader("Add available times")
            first_date = st.date_input("Start from", min_value=date.today(), value=date.today() + timedelta(days=1), key="tutor_first_date")
            days = st.multiselect("Available weekdays", list(WEEKDAYS), default=("Tuesday", "Thursday"), key="tutor_weekdays")
            weeks = st.slider("Repeat for", 1, 12, 4, format="%d weeks", key="tutor_weeks")
            c1, c2, c3, c4 = st.columns(4)
            start = c1.time_input("From", time(16, 0), key="tutor_start")
            end = c2.time_input("Until", time(19, 0), key="tutor_end")
            duration = c3.selectbox("Lesson length", (30, 45, 60), index=2, format_func=lambda value: f"{value} min", key="tutor_duration")
            gap = c4.selectbox("Break between", (0, 10, 15, 30), index=2, format_func=lambda value: f"{value} min", key="tutor_gap")
            create_slots = st.form_submit_button("Create available times", type="primary", use_container_width=True)
        if create_slots:
            try:
                count = tutor_add_recurring_slots(str(assignment["tutor_id"]), first_date, [WEEKDAYS[day] for day in days], weeks, start, end, duration, gap, chosen_timezone, access_token(), user)
                flash("success", f"Created {count} new available time{'s' if count != 1 else ''}. Existing duplicates were skipped.")
                st.rerun()
            except Exception as exc:
                st.error(friendly_error(exc))

        try:
            own_slots = tutor_slots(access_token(), user)
        except Exception as exc:
            st.error(friendly_error(exc))
            own_slots = []
        future_open = [slot for slot in own_slots if slot.get("status") == "open" and datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00")) > datetime.now(ZoneInfo("UTC"))]
        st.subheader("Edit open times")
        if not future_open:
            st.info("No future open times to edit.")
        for slot in future_open:
            local_start = datetime.fromisoformat(str(slot["starts_at"]).replace("Z", "+00:00")).astimezone(ZoneInfo(chosen_timezone))
            local_end = datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00")).astimezone(ZoneInfo(chosen_timezone))
            with st.expander(format_slot(slot, chosen_timezone)):
                with st.form(f"edit_own_slot_{slot['id']}"):
                    slot_date = st.date_input("Date", value=local_start.date(), min_value=date.today(), key=f"slot_date_{slot['id']}")
                    c1, c2 = st.columns(2)
                    slot_start = c1.time_input("Starts", value=local_start.time().replace(tzinfo=None), key=f"slot_start_{slot['id']}")
                    slot_end = c2.time_input("Ends", value=local_end.time().replace(tzinfo=None), key=f"slot_end_{slot['id']}")
                    save_slot, remove_slot = st.columns(2)
                    update_slot = save_slot.form_submit_button("Save changes", type="primary", use_container_width=True)
                    cancel_slot = remove_slot.form_submit_button("Remove time", use_container_width=True)
                try:
                    if update_slot:
                        tutor_update_open_slot(str(slot["id"]), slot_date, slot_start, slot_end, chosen_timezone, access_token(), user)
                        flash("success", "Available time updated.")
                        st.rerun()
                    if cancel_slot:
                        tutor_cancel_open_slot(str(slot["id"]), access_token(), user)
                        flash("success", "Available time removed.")
                        st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))


def owner_dashboard(user: dict | None) -> None:
    st.markdown('<div class="app-page-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown('<h1 class="inner-page-title">Owner dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="area-kicker">PRIVATE MANAGER SPACE</p>', unsafe_allow_html=True)
    st.caption("Publish approved student tutors, generate clear dated availability, and manage every request.")
    if not is_owner(user):
        message = "Sign in with an approved owner account to open this dashboard." if not user else "This signed-in account does not have owner access."
        st.error(message)
        if st.button("Go to sign in", type="primary"):
            st.session_state.return_page_after_auth = "Owner dashboard"
            go("My account")
            st.rerun()
        return

    section = st.radio(
        "Owner section", ("Tutors", "Tutor access", "Availability", "Session requests"),
        index=0, key="owner_section", label_visibility="collapsed", horizontal=True,
    )

    if section == "Tutors":
        st.markdown('<p class="area-kicker dashboard-section">APPROVED TUTOR DIRECTORY</p>', unsafe_allow_html=True)
        version = int(st.session_state.get("tutor_form_version", 0))
        with st.form(f"add_tutor_{version}", clear_on_submit=False):
            st.subheader("Add an approved tutor")
            st.caption("Tutor contact details stay private. Availability is created separately after publishing.")
            name = st.text_input("Public tutor name", placeholder="First name and last initial", max_chars=80, key=f"new_tutor_name_{version}")
            email = st.text_input("Private tutor email", key=f"new_tutor_email_{version}")
            age, grade_column, country_column = st.columns(3)
            age_value = age.number_input("Age", 13, 18, 15, key=f"new_tutor_age_{version}")
            grade_value = grade_column.selectbox("Tutor grade", GRADES, index=9, key=f"new_tutor_grade_{version}")
            country_value = country_column.selectbox("Country", COUNTRIES, key=f"new_tutor_country_{version}")
            subjects = st.multiselect("Subjects taught", SUBJECTS, key=f"new_tutor_subjects_{version}")
            languages = st.multiselect("Languages", LANGUAGES, key=f"new_tutor_languages_{version}")
            grade_range = st.select_slider("Student grades they teach", GRADES, value=(1, 6), key=f"new_tutor_range_{version}")
            bio = st.text_area("Public introduction", max_chars=800, placeholder="A short, friendly introduction for students and families", key=f"new_tutor_bio_{version}")
            active = st.checkbox("Approved and visible in public search", value=True, key=f"new_tutor_active_{version}")
            add = st.form_submit_button("Publish tutor  →", type="primary", use_container_width=True, disabled=bool(st.session_state.get("tutor_publish_in_progress")))
        if add:
            st.session_state.tutor_publish_in_progress = True
            try:
                errors = []
                if not name.strip(): errors.append("Enter the public tutor name.")
                if not subjects: errors.append("Choose at least one subject.")
                if not languages: errors.append("Choose at least one language.")
                if not bio.strip(): errors.append("Add a short public introduction.")
                if grade_range[0] > grade_range[1]: errors.append("The minimum student grade must not exceed the maximum.")
                if errors:
                    raise ValueError(" ".join(errors))
                payload = {"full_name": name.strip(), "tutor_email": normal_email(email), "age": int(age_value), "school_grade": int(grade_value), "country": country_value, "subjects": list(subjects), "languages": list(languages), "min_student_grade": int(grade_range[0]), "max_student_grade": int(grade_range[1]), "bio": bio.strip(), "active": bool(active)}
                with st.spinner("Publishing tutor securely…"):
                    saved = add_tutor(payload, user)
                st.session_state.tutor_publish_in_progress = False
                st.session_state.tutor_form_version = version + 1
                st.session_state.tutor_success = f"{saved['full_name']} was published successfully. Add lesson times in Availability."
                st.rerun()
            except Exception as exc:
                st.session_state.tutor_publish_in_progress = False
                st.error(friendly_error(exc))
        success = st.session_state.pop("tutor_success", None)
        if success:
            st.success(success)
        try:
            tutors = managed_tutors(user)
        except Exception as exc:
            st.error(friendly_error(exc))
            tutors = []
        st.subheader("Tutor directory")
        if not tutors:
            st.info("No tutors have been added yet.")
        for tutor in tutors:
            visibility = "LIVE" if tutor["active"] else "HIDDEN"
            with st.expander(f"{tutor['full_name']} — {tutor['country']} — {visibility}"):
                st.markdown(f'<span class="reservation-status {"status-confirmed" if tutor["active"] else "status-cancelled"}">{visibility}</span>', unsafe_allow_html=True)
                st.write(f"**Private email:** {tutor['tutor_email']}  \n**Subjects:** {', '.join(tutor['subjects'])}  \n**Languages:** {', '.join(tutor['languages'])}  \n**Teaches:** Grades {tutor['min_student_grade']}–{tutor['max_student_grade']}")
                st.caption(tutor["bio"])
                with st.form(f"edit_tutor_{tutor['id']}"):
                    st.markdown("#### Edit tutor")
                    edit_name = st.text_input("Public name", value=tutor["full_name"], key=f"edit_name_{tutor['id']}")
                    edit_email = st.text_input("Private email", value=tutor["tutor_email"], key=f"edit_email_{tutor['id']}")
                    e1, e2, e3 = st.columns(3)
                    edit_age = e1.number_input("Age", 13, 18, int(tutor["age"]), key=f"edit_age_{tutor['id']}")
                    edit_grade = e2.selectbox("Tutor grade", GRADES, index=GRADES.index(int(tutor["school_grade"])), key=f"edit_grade_{tutor['id']}")
                    edit_country = e3.selectbox("Country", COUNTRIES, index=COUNTRIES.index(tutor["country"]), key=f"edit_country_{tutor['id']}")
                    edit_subjects = st.multiselect("Subjects", SUBJECTS, default=[item for item in tutor["subjects"] if item in SUBJECTS], key=f"edit_subjects_{tutor['id']}")
                    edit_languages = st.multiselect("Languages", LANGUAGES, default=[item for item in tutor["languages"] if item in LANGUAGES], key=f"edit_languages_{tutor['id']}")
                    edit_range = st.select_slider("Student grades taught", GRADES, value=(int(tutor["min_student_grade"]), int(tutor["max_student_grade"])), key=f"edit_range_{tutor['id']}")
                    edit_bio = st.text_area("Public introduction", value=tutor["bio"], max_chars=800, key=f"edit_bio_{tutor['id']}")
                    edit_active = st.checkbox("Visible in public search", value=bool(tutor["active"]), key=f"edit_active_{tutor['id']}")
                    delete_confirmed = st.checkbox("I understand that deleting this tutor removes them and cancels their unreserved times.", key=f"delete_confirm_{tutor['id']}")
                    save_column, delete_column = st.columns(2)
                    save_tutor = save_column.form_submit_button("Save tutor changes", type="primary", use_container_width=True)
                    remove_tutor = delete_column.form_submit_button("Delete tutor", use_container_width=True)
                if remove_tutor:
                    try:
                        if not delete_confirmed:
                            raise ValueError("Tick the confirmation box before deleting this tutor.")
                        with st.spinner("Deleting tutor…"):
                            delete_tutor(str(tutor["id"]), user)
                        flash("success", f"{tutor['full_name']} was deleted. Existing reservation history was kept safely.")
                        st.rerun()
                    except Exception as exc:
                        st.error(friendly_error(exc))
                elif save_tutor:
                    try:
                        if not edit_name.strip() or not edit_subjects or not edit_languages or not edit_bio.strip():
                            raise ValueError("Complete the name, subjects, languages, and public introduction.")
                        values = {"full_name": edit_name.strip(), "tutor_email": normal_email(edit_email), "age": int(edit_age), "school_grade": int(edit_grade), "country": edit_country, "subjects": list(edit_subjects), "languages": list(edit_languages), "min_student_grade": int(edit_range[0]), "max_student_grade": int(edit_range[1]), "bio": edit_bio.strip(), "active": bool(edit_active)}
                        with st.spinner("Saving tutor changes…"):
                            update_tutor(str(tutor["id"]), values, user)
                        flash("success", "Tutor changes saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(friendly_error(exc))

    elif section == "Tutor access":
        st.markdown('<p class="area-kicker dashboard-section">SECURE TUTOR ACCESS</p>', unsafe_allow_html=True)
        st.subheader("Assign a Tutor Dashboard")
        st.caption("Choose an approved tutor and enter the exact email they will verify and use to sign in. Only owners can change these assignments.")
        try:
            tutors = managed_tutors(user)
            assignments = tutor_role_assignments(user)
        except Exception as exc:
            st.error(friendly_error(exc))
            tutors, assignments = [], []
        active_tutors = [item for item in tutors if item.get("active")]
        if not active_tutors:
            st.info("Publish an active tutor before assigning dashboard access.")
        else:
            labels = {str(item["id"]): item["full_name"] for item in active_tutors}
            with st.form("assign_tutor_access"):
                tutor_id = st.selectbox("Tutor profile", list(labels), format_func=labels.get)
                role_email = st.text_input("Tutor account email", placeholder="tutor@example.com")
                assign_role = st.form_submit_button("Assign Tutor role", type="primary", use_container_width=True)
            if assign_role:
                try:
                    assign_tutor_role(tutor_id, normal_email(role_email), user)
                    flash("success", "Tutor access assigned. The dashboard unlocks after this exact email verifies its account and signs in.")
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))
        st.subheader("Current Tutor roles")
        if not assignments:
            st.info("No Tutor Dashboard access has been assigned yet.")
        for role in assignments:
            role_tutor = related_record(role.get("tutors"))
            left, right = st.columns((5, 1))
            left.markdown(
                f'<div class="dashboard-item"><span class="reservation-status status-confirmed">TUTOR</span>'
                f'<strong>{escape(role_tutor.get("full_name") or "Tutor profile")}</strong>'
                f'<small>{escape(role["email"])} · {escape(role["timezone"])}</small></div>', unsafe_allow_html=True,
            )
            if right.button("Remove role", key=f"remove_role_{role['id']}", use_container_width=True):
                try:
                    remove_tutor_role(str(role["id"]), user)
                    flash("success", "Tutor access removed. The tutor profile and booking history were kept.")
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))

    elif section == "Availability":
        st.markdown('<p class="area-kicker dashboard-section">LESSON AVAILABILITY</p>', unsafe_allow_html=True)
        try:
            tutors = approved_tutors(user)
        except Exception as exc:
            st.error(friendly_error(exc))
            tutors = []
        if not tutors:
            st.info("Add a tutor first.")
        else:
            labels = {item["id"]: item["full_name"] for item in tutors}
            tutor_id = st.selectbox("Tutor", list(labels), format_func=labels.get, key="schedule_tutor")
            with st.form("recurring_schedule"):
                st.subheader("Generate open lesson times")
                st.caption("Choose a weekly window and TM Tutoring will create evenly spaced bookable lessons.")
                first_date = st.date_input("Start from", min_value=date.today(), value=date.today() + timedelta(days=1))
                days = st.multiselect("Available weekdays", list(WEEKDAYS), default=("Tuesday", "Thursday"))
                weeks = st.slider("Repeat for", 1, 12, 4, format="%d weeks")
                c1, c2, c3, c4 = st.columns(4)
                start = c1.time_input("From", time(16, 0))
                end = c2.time_input("Until", time(19, 0))
                duration = c3.selectbox("Lesson length", (30, 45, 60), index=2, format_func=lambda value: f"{value} min")
                gap = c4.selectbox("Break between", (0, 10, 15, 30), index=2, format_func=lambda value: f"{value} min")
                timezone_name = st.selectbox("Tutor timezone", TIMEZONES)
                generate = st.form_submit_button("Generate lesson times", type="primary")
            if generate:
                try:
                    count = add_recurring_slots(tutor_id, first_date, [WEEKDAYS[day] for day in days], weeks, start, end, duration, gap, timezone_name, user)
                    flash("success", f"Created {count} new lesson times. Existing duplicates were skipped.")
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))
            try:
                slots = upcoming_slots(tutor_id, user)
            except Exception as exc:
                st.error(friendly_error(exc))
                slots = []
            st.subheader("Upcoming times")
            if not slots:
                st.info("No upcoming times.")
            for slot in slots:
                left, right = st.columns((5, 1))
                left.write(f"{format_slot(slot)} — **{slot['status'].title()}**")
                if slot["status"] == "open" and right.button("Remove", key=f"slot_{slot['id']}"):
                    try:
                        cancel_open_slot(slot["id"], user)
                        flash("success", "Open time removed.")
                        st.rerun()
                    except Exception as exc:
                        st.error(friendly_error(exc))

    else:
        st.markdown('<p class="area-kicker dashboard-section">RESERVATION MANAGEMENT</p>', unsafe_allow_html=True)
        try:
            requests = all_session_requests(user)
        except Exception as exc:
            st.error(friendly_error(exc))
            requests = []
        if not requests:
            st.info("No session requests yet.")
        else:
            labels = {item["id"]: f"{item['student_first_name']} → {item['tutors']['full_name']} — {item['subject']} — {item['status']}" for item in requests}
            request_id = st.selectbox("Request", list(labels), format_func=labels.get)
            selected = next(item for item in requests if item["id"] == request_id)
            st.write(f"**Guardian:** {selected['guardian_name']} — {selected['guardian_email']}  \n**Time:** {format_slot(selected['availability_slots'])}  \n**Notes:** {selected['notes'] or 'None'}")
            transitions = {"requested": ("confirmed", "cancelled", "declined"), "confirmed": ("completed", "cancelled")}
            choices = transitions.get(selected["status"], ())
            status = st.selectbox("New status", choices) if choices else None
            meeting_url = st.text_input("Lesson link", value=selected.get("meeting_url") or "", placeholder="https://meet.google.com/...") if choices else ""
            if not choices:
                st.info("This request is closed and cannot be changed.")
            if choices and st.button("Save status and email everyone", type="primary"):
                try:
                    safe_url = valid_meeting_url(meeting_url)
                    if status == "confirmed" and not safe_url:
                        raise ValueError("Add a secure lesson link before confirming.")
                    updated = change_session_status(request_id, status, safe_url, user)
                    emailed = notify_session_status(updated)
                    flash("success", "Status saved and everyone was emailed." if emailed else "Status saved. Email delivery needs checking.")
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))


user = current_user()
known_pages = ("Home", "Find a tutor", "My account", "Tutor dashboard", "Owner dashboard")
if st.session_state.get("page") not in known_pages:
    st.session_state.page = "Home"
show_owner_page = is_owner(user) or st.session_state.get("page") == "Owner dashboard"
try:
    show_tutor_page = bool(tutor_assignment(user)) or st.session_state.get("page") == "Tutor dashboard"
except Exception:
    show_tutor_page = st.session_state.get("page") == "Tutor dashboard"
pages = ["Home", "Find a tutor", "My account"] + (["Tutor dashboard"] if show_tutor_page else []) + (["Owner dashboard"] if show_owner_page else [])
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><span class="sidebar-brand-mark">TM</span><div><strong>TM Tutoring</strong><small>Student learning hub</small></div></div>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-label">NAVIGATION</p>', unsafe_allow_html=True)
    selected = st.radio("Menu", pages, index=pages.index(st.session_state.page), label_visibility="collapsed")
    st.session_state.page = selected
    account_text = escape(user["email"]) if user else "Guest visitor"
    account_state = "Signed in" if user else "Not signed in"
    st.markdown(f'<div class="sidebar-account"><span></span><div><strong>{account_state}</strong><small>{account_text}</small></div></div>', unsafe_allow_html=True)
    if configuration_missing():
        st.warning("Setup is not finished. Connect the missing services before accepting real bookings.")

show_flash()
{"Home": home, "Find a tutor": find_tutor, "My account": account, "Tutor dashboard": tutor_dashboard, "Owner dashboard": owner_dashboard}[st.session_state.page](user)
