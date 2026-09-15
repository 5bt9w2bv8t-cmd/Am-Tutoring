from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from email_validator import EmailNotValidError, validate_email

from auth import access_token, current_user, is_owner, reset_password_with_code, send_password_code, sign_in, sign_out, sign_up
from backend import add_recurring_slots, add_tutor, all_session_requests, approved_tutors, cancel_open_slot, change_session_status, configuration_missing, friendly_error, open_slots, public_tutors, request_session, set_tutor_active, upcoming_slots, user_session_requests
from core import COUNTRIES, GRADES, LANGUAGES, SUBJECTS, TIMEZONES, WEEKDAYS, format_slot, valid_meeting_url
from mailer import notify_session_request, notify_session_status


st.set_page_config(page_title="AM Tutoring", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")
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


def home(user: dict | None) -> None:
    st.markdown('<header class="site-header"><a class="brand" href="#top"><span class="brand-mark">AM</span><span>AM Tutoring</span></a><nav><a href="#about">About</a><a href="#safety">Help &amp; Safety</a></nav></header><div id="top"></div>', unsafe_allow_html=True)
    st.markdown('<section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="live-dot"></span> Student-led · Online · Free</div><h1>Students helping<br>students <em>grow.</em></h1><p class="hero-lede">AM Tutoring connects school students in Syria and the UAE with approved student tutors for friendly, free online support.</p></div><div class="hero-board" aria-label="How AM Tutoring works"><div class="tape tape-one"></div><div class="tape tape-two"></div><div class="board-note note-yellow"><span class="note-kicker">STUDENT</span><strong>Choose what<br>you need.</strong><span class="scribble">〰</span></div><div class="board-note note-white"><div class="mini-avatar">AM</div><div><span class="note-kicker">A GOOD MATCH</span><strong>Pick a tutor + time</strong><small>Send a guardian-led request</small></div><span class="play">→</span></div><div class="board-note note-blue"><span class="star">✦</span><strong>Learn.<br>Help.<br>Grow.</strong><small>تعلم • ساعد • انمو</small></div><div class="pencil-line"></div></div></section>', unsafe_allow_html=True)
    if st.button("Find a free tutor  →", type="primary", key="hero_find"):
        go("Find a tutor")
        st.rerun()
    st.markdown('<div class="micro-proof"><span>✓</span> Always free &nbsp; <span>✓</span> Guardian-approved &nbsp; <span>✓</span> Arabic &amp; English</div><div class="ticker"><span>LEARN TOGETHER</span><b>✦</b><span>SHARE WHAT YOU KNOW</span><b>✦</b><span>GROW WITH AM TUTORING</span></div><section class="start-band"><div><span>Start here</span><h2>Find the right tutor in five simple steps.</h2><p>Choose the student’s country, grade and subject, then select an approved tutor and available time.</p></div></section><section class="about section" id="about"><div class="section-label">WHAT AM TUTORING DOES</div><div class="about-grid"><h2>A simple way for students to help each other.</h2><div class="about-copy"><p>Families find support by country, grade, and subject. Approved student tutors share the subjects and times they can offer.</p><p>Every session request is managed through a guardian, giving students a welcoming way to learn and volunteer safely.</p></div></div><div class="impact-row"><div><strong>100%</strong><span>Free for families</span></div><div><strong>13–18</strong><span>Student tutor ages</span></div><div><strong>2</strong><span>Countries connected</span></div><div><strong>1:1</strong><span>Focused support</span></div></div></section><section class="how section"><div class="section-label">HOW IT WORKS</div><div class="section-heading-row"><h2>Small steps.<br>Real progress.</h2><p>Everything is designed to make finding help feel clear, friendly, and safe.</p></div><div class="steps"><article><div class="step-icon">⌕</div><h3>Choose what you need</h3><p>Select a country, grade, and subject to see suitable tutors.</p></article><article><div class="step-icon">→</div><h3>Pick a tutor + time</h3><p>Compare approved student profiles and open lesson times.</p></article><article><div class="step-icon">✦</div><h3>Learn, help, grow</h3><p>A guardian requests the session and receives every update.</p></article></div></section><section class="safety section" id="safety"><div class="safety-card"><div class="safety-graphic"><span>✓</span><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div></div><div><div class="section-label">STUDENT SAFETY</div><h2>Guardians stay in the loop.</h2><p>Every session request is managed through a guardian. Tutor profiles are reviewed before they appear, and no private contact details are displayed.</p><ul><li><span>✓</span> Tutor profiles require owner approval</li><li><span>✓</span> Guardians receive session communication</li><li><span>✓</span> No private student contact is displayed</li></ul></div></div></section><section class="tutor-contact"><div><span>STUDENT VOLUNTEERS</span><h2>Want to tutor?</h2><p>Email your CV, age, grade, subjects, languages, and available times to the AM Tutoring manager. Student tutors must be ages 13–18.</p></div><div class="tutor-contact-action"><a class="button button-light" href="mailto:taleenalali5@gmail.com?subject=AM%20Tutoring%20Volunteer">Email about tutoring <span>↗</span></a><small>taleenalali5@gmail.com</small></div></section><footer><a class="brand" href="#top"><span class="brand-mark">AM</span><span>AM Tutoring</span></a><p>Students helping students in Syria and the UAE.</p><small>© 2026 AM Tutoring. Free, student-led learning.</small></footer>', unsafe_allow_html=True)


def find_tutor(user: dict | None) -> None:
    st.markdown('<h1 class="inner-page-title">Find a tutor</h1>', unsafe_allow_html=True)
    st.caption("Choose your learning needs, then reserve a real available lesson time.")
    filters = st.columns(3)
    country = filters[0].selectbox("Country", COUNTRIES)
    grade = filters[1].selectbox("Student grade", GRADES, format_func=lambda item: f"Grade {item}")
    subject = filters[2].selectbox("Subject", SUBJECTS)
    search = {"country": country, "grade": grade, "subject": subject}
    if st.button("Show matching tutors", type="primary"):
        try:
            st.session_state.matches = public_tutors(country, grade, subject)
            st.session_state.search = search
            st.session_state.pop("reservation_tutor", None)
            st.session_state.pop("reservation_step", None)
        except Exception as exc:
            st.error(friendly_error(exc))
            return
    if st.session_state.get("search") != search:
        st.info("Choose the filters above, then show matching tutors.")
        return
    tutors = st.session_state.get("matches", [])
    if not tutors:
        st.info("No approved tutor currently matches. Try another subject or check again later.")
        return
    labels = {item["id"]: f"{item['full_name']} — Grade {item['school_grade']} — {item['country']}" for item in tutors}
    tutor_id = st.selectbox("Choose a tutor", list(labels), format_func=labels.get, key="match_tutor")
    tutor = next(item for item in tutors if item["id"] == tutor_id)
    with st.container(border=True):
        st.subheader(tutor["full_name"])
        st.write(tutor["bio"])
        st.caption(f"Subjects: {', '.join(tutor['subjects'])}  ·  Languages: {', '.join(tutor['languages'])}  ·  Teaches grades {tutor['min_student_grade']}–{tutor['max_student_grade']}")
        if not user:
            st.warning("Sign in first so your reservation and confirmation history can be saved securely.")
            if st.button("Sign in to reserve this tutor", key="reserve_sign_in"):
                go("My account")
                st.rerun()
            return
        if not (st.session_state.get("reservation_tutor") == tutor_id and st.session_state.get("reservation_step") == 4):
            if st.button(f"Reserve with {tutor['full_name'].split()[0]}  →", type="primary", key="reserve_tutor"):
                st.session_state.reservation_tutor = tutor_id
                st.session_state.reservation_step = 1
                st.session_state.pop("reservation_date", None)
                st.session_state.pop("reservation_slot_id", None)
                st.rerun()
    if st.session_state.get("reservation_tutor") == tutor_id and st.session_state.get("reservation_step") == 4 and st.session_state.get("reservation_confirmation"):
        booking, emailed = st.session_state.reservation_confirmation
        st.markdown('<div class="reservation-progress"><span class="complete">1 · Date</span><span class="complete">2 · Time</span><span class="complete">3 · Details</span><span class="active">4 · Confirmation</span></div>', unsafe_allow_html=True)
        st.success("Reservation saved. " + ("Email copies were sent." if emailed else "You can track the status in My account."))
        st.markdown(f'<div class="reservation-summary"><b>Request received</b><span>{tutor["full_name"]} · {subject} · Grade {grade}</span><span>{format_slot(booking["availability_slots"])}</span></div>', unsafe_allow_html=True)
        if st.button("Make another reservation", key="another_reservation"):
            for key in ("reservation_tutor", "reservation_step", "reservation_date", "reservation_slot_id", "reservation_confirmation", "booking_submitting"):
                st.session_state.pop(key, None)
            st.rerun()
        return
    try:
        slots = open_slots(tutor_id)
    except Exception as exc:
        st.error(friendly_error(exc))
        return
    available = [slot for slot in slots if slot["status"] == "open"]
    unavailable = [slot for slot in slots if slot["status"] != "open"]
    if unavailable:
        with st.expander(f"Filled or pending times ({len(unavailable)})"):
            for slot in unavailable:
                st.markdown(f'<div class="slot-unavailable"><span>{format_slot(slot)}</span><b>{"Pending" if slot["status"] == "requested" else "Filled"}</b></div>', unsafe_allow_html=True)
    if not available:
        st.info("All upcoming times are filled or waiting for confirmation.")
        return
    if st.session_state.get("reservation_tutor") != tutor_id:
        return
    step = st.session_state.get("reservation_step", 1)
    st.markdown('<div class="reservation-progress"><span class="active">1 · Date</span><span class="active">2 · Time</span><span>3 · Details</span><span>4 · Confirmation</span></div>', unsafe_allow_html=True)
    def local_date(slot: dict) -> date:
        return datetime.fromisoformat(slot["starts_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(slot["timezone"])).date()
    dates = sorted({local_date(slot) for slot in available})
    date_labels = {item.isoformat(): item.strftime("%A, %d %B %Y") for item in dates}
    chosen_date_key = st.selectbox("1. Choose a date", list(date_labels), format_func=date_labels.get, key="reservation_date")
    day_slots = [slot for slot in available if local_date(slot).isoformat() == chosen_date_key]
    slot_labels = {slot["id"]: datetime.fromisoformat(slot["starts_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(slot["timezone"])).strftime("%H:%M") + "–" + datetime.fromisoformat(slot["ends_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(slot["timezone"])).strftime("%H:%M") + f" · {slot['timezone'].replace('Asia/', '')}" for slot in day_slots}
    slot_id = st.selectbox("2. Choose an available time", list(slot_labels), format_func=slot_labels.get, key="reservation_slot_id")
    st.caption("Open times are selectable. Filled or pending times are shown above and cannot be selected.")
    if step < 2 and st.button("Continue to your details  →", type="primary", key="continue_details"):
        st.session_state.reservation_step = 2
        st.rerun()
    if st.session_state.get("reservation_step", 1) < 2:
        return
    selected_slot = next(slot for slot in day_slots if slot["id"] == slot_id)
    st.markdown(f'<div class="reservation-summary"><b>{tutor["full_name"]}</b><span>{subject} · Grade {grade}</span><span>{format_slot(selected_slot)}</span></div>', unsafe_allow_html=True)
    with st.form("session_request", clear_on_submit=False):
        st.subheader("3. Your details")
        student_name = st.text_input("Student’s first name only", max_chars=50)
        guardian_name = st.text_input("Parent or guardian name", max_chars=100)
        st.text_input("Confirmation email", value=user["email"], disabled=True)
        notes = st.text_area("What help is needed?", max_chars=1000, placeholder="A topic, assignment, or learning goal")
        consent = st.checkbox("I am the parent/guardian or have their permission, and I agree to receive session emails.")
        submitted = st.form_submit_button("Send reservation request  →", type="primary", use_container_width=True)
    if submitted:
        if st.session_state.get("booking_submitting"):
            st.warning("Your reservation is already being submitted.")
            return
        st.session_state.booking_submitting = True
        try:
            if not student_name.strip() or not guardian_name.strip() or not consent:
                raise ValueError("Complete the names and guardian consent.")
            booking = request_session({"p_tutor_id": tutor_id, "p_slot_id": slot_id, "p_student_first_name": student_name.strip(), "p_student_country": country, "p_student_grade": grade, "p_subject": subject, "p_guardian_name": guardian_name.strip(), "p_guardian_email": user["email"], "p_notes": notes.strip()}, access_token())
            emailed = notify_session_request(booking)
            st.session_state.reservation_confirmation = (booking, emailed)
            st.session_state.reservation_step = 4
            st.session_state.booking_submitting = False
            st.rerun()
        except Exception as exc:
            st.session_state.booking_submitting = False
            st.error(friendly_error(exc))
def account(user: dict | None) -> None:
    st.markdown('<h1 class="inner-page-title">My account</h1>', unsafe_allow_html=True)
    st.markdown('<p class="area-kicker">YOUR AM TUTORING</p>', unsafe_allow_html=True)
    st.caption("Sign in to request lessons and keep every reservation detail in one place.")
    if not user:
        sign_in_tab, create_tab, reset_tab = st.tabs(("Sign in", "Create account", "Reset password"))
        with sign_in_tab, st.form("sign_in"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Sign in", type="primary"):
                try:
                    sign_in(normal_email(email), password)
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))
        with create_tab, st.form("create_account"):
            email = st.text_input("Parent, guardian, or tutor email", key="signup_email")
            password = st.text_input("Create password", type="password", key="signup_password", help="Use at least 8 characters.")
            confirm = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account", type="primary"):
                try:
                    if len(password) < 8 or password != confirm:
                        raise ValueError("Use at least 8 characters and make both passwords match.")
                    active = sign_up(normal_email(email), password)
                    if active:
                        st.rerun()
                    st.success("Account created. Check your email to confirm it, then sign in.")
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
        rows = user_session_requests(access_token())
    except Exception as exc:
        st.error(friendly_error(exc))
        return
    st.subheader("Session history")
    st.caption("Your reservation status and lesson links appear here after the owner reviews a request.")
    if not rows:
        st.info("No booking history yet.")
    for item in rows:
        with st.container(border=True):
            st.markdown(f'<span class="reservation-status status-{item["status"]}">{item["status"].upper()}</span>', unsafe_allow_html=True)
            st.subheader(f"{item['subject']} with {item['tutors']['full_name']}")
            st.write(format_slot(item["availability_slots"]))
            st.write(f"Student: {item['student_first_name']}")
            if item.get("meeting_url") and item["status"] == "confirmed":
                st.link_button("Open lesson", item["meeting_url"])


def owner_dashboard(user: dict | None) -> None:
    st.markdown('<h1 class="inner-page-title">Owner dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="area-kicker">PRIVATE MANAGER SPACE</p>', unsafe_allow_html=True)
    st.caption("Publish approved student tutors, generate clear dated availability, and manage every request.")
    if not is_owner(user):
        st.error("This page is available only to the AM Tutoring owner account.")
        return
    tutors_tab, schedule_tab, requests_tab = st.tabs(("Tutors", "Availability", "Session requests"))
    with tutors_tab:
        with st.form("add_tutor", clear_on_submit=True):
            st.subheader("Add an approved tutor")
            name = st.text_input("Public name", placeholder="First name and last initial", max_chars=80)
            email = st.text_input("Tutor email — private")
            age, grade_column, country_column = st.columns(3)
            age_value = age.number_input("Age", 13, 18, 15)
            grade_value = grade_column.selectbox("Tutor grade", GRADES, index=9)
            country_value = country_column.selectbox("Country", COUNTRIES)
            subjects = st.multiselect("Subjects", SUBJECTS)
            languages = st.multiselect("Languages", LANGUAGES)
            grade_range = st.select_slider("Grades they teach", GRADES, value=(1, 6))
            bio = st.text_area("Public introduction", max_chars=800)
            add = st.form_submit_button("Publish tutor", type="primary")
        if add:
            try:
                if not name.strip() or not subjects or not languages or not bio.strip():
                    raise ValueError("Complete every tutor field.")
                add_tutor({"full_name": name.strip(), "tutor_email": normal_email(email), "age": age_value, "school_grade": grade_value, "country": country_value, "subjects": subjects, "languages": languages, "min_student_grade": grade_range[0], "max_student_grade": grade_range[1], "bio": bio.strip()}, user)
                flash("success", "Tutor published.")
                st.rerun()
            except Exception as exc:
                st.error(friendly_error(exc))
        try:
            tutors = approved_tutors(user)
        except Exception as exc:
            st.error(friendly_error(exc))
            tutors = []
        for tutor in tutors:
            with st.expander(f"{tutor['full_name']} — {tutor['country']}"):
                st.write(f"**Email:** {tutor['tutor_email']}  \n**Subjects:** {', '.join(tutor['subjects'])}")
                if st.button("Remove from public list", key=f"remove_{tutor['id']}"):
                    try:
                        set_tutor_active(tutor["id"], False, user)
                        flash("success", "Tutor removed from the public list.")
                        st.rerun()
                    except Exception as exc:
                        st.error(friendly_error(exc))
    with schedule_tab:
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
    with requests_tab:
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
pages = ["Home", "Find a tutor", "My account"] + (["Owner dashboard"] if is_owner(user) else [])
if st.session_state.get("page") not in pages:
    st.session_state.page = "Home"
with st.sidebar:
    st.markdown("## AM Tutoring")
    selected = st.radio("Menu", pages, index=pages.index(st.session_state.page), label_visibility="collapsed")
    st.session_state.page = selected
    st.caption(f"Signed in: {user['email']}" if user else "Not signed in")

show_flash()
if configuration_missing():
    st.warning("Setup is not finished. The owner must connect Supabase and Resend before accepting real bookings.")
{"Home": home, "Find a tutor": find_tutor, "My account": account, "Owner dashboard": owner_dashboard}[st.session_state.page](user)
