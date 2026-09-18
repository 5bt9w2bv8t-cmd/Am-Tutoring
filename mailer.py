from __future__ import annotations

from html import escape
from typing import Any

import resend

from backend import email_was_sent, log_email, secret
from core import format_slot


def send_email(*, event_type: str, to: str, subject: str, html: str, related_id: str = "") -> bool:
    api_key, sender = secret("RESEND_API_KEY"), secret("FROM_EMAIL")
    recipient = str(to or "").strip().lower()
    if not recipient:
        log_email(event_type, recipient or "unknown", subject, "failed", error="Recipient email is missing", related_id=related_id)
        return False
    # Confirmation and terminal status messages are idempotent. A repeated
    # ``confirmed`` status may legitimately carry a newly added lesson link,
    # so that event is allowed to send again after the owner edits the link.
    if not event_type.startswith("session_status_confirmed_") and email_was_sent(event_type, recipient, related_id):
        return True
    if not api_key or not sender:
        log_email(event_type, recipient, subject, "failed", error="Resend is not configured", related_id=related_id)
        return False
    resend.api_key = api_key
    try:
        result = resend.Emails.send({"from": sender, "to": [recipient], "subject": subject, "html": html})
        provider_id = result.get("id", "") if isinstance(result, dict) else str(getattr(result, "id", ""))
        log_email(event_type, recipient, subject, "sent", provider_id=provider_id, related_id=related_id)
        return True
    except Exception as exc:
        error = str(exc).replace(api_key, "[redacted]")[:500]
        log_email(event_type, recipient, subject, "failed", error=error, related_id=related_id)
        return False


def _recipients(request: dict[str, Any]) -> set[str]:
    return {
        email.strip().lower()
        for email in (
            request["tutors"].get("tutor_email", ""),
            request.get("guardian_email", ""),
        )
        if email and email.strip()
    }


def _record(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def notify_session_request(request: dict[str, Any], recipients: set[str] | None = None) -> bool:
    tutor, slot = _record(request.get("tutors")), _record(request.get("availability_slots"))
    student = escape(request["student_first_name"])
    guardian = escape(request.get("guardian_name", "Guardian"))
    tutor_name = escape(tutor["full_name"])
    subject_grade = f"{escape(request['subject'])} · Grade {request['student_grade']}"
    notes = escape(request.get("notes") or "No additional learning notes")
    def details(timezone_name: str) -> str:
        lesson_time = escape(format_slot(slot, timezone_name))
        return (
            '<div style="margin:22px 0;padding:18px;border:1px solid #d8d2c7;border-radius:12px;background:#fffdf8">'
            f'<p style="margin:0 0 8px"><b>Tutor:</b> {tutor_name}</p>'
            f'<p style="margin:0 0 8px"><b>Student:</b> {student}</p>'
            f'<p style="margin:0 0 8px"><b>Guardian / reserver:</b> {guardian}</p>'
            f'<p style="margin:0 0 8px"><b>Subject:</b> {subject_grade}</p>'
            f'<p style="margin:0 0 8px"><b>Date and time:</b> {lesson_time}</p>'
            f'<p style="margin:0 0 8px"><b>Status:</b> Confirmed</p>'
            f'<p style="margin:0"><b>Learning notes:</b> {notes}</p></div>'
        )
    reserver_html = (
        '<div style="font-family:Arial,sans-serif;color:#10253b;line-height:1.55;max-width:620px">'
        '<div style="display:inline-block;padding:7px 11px;background:#315fe7;color:white;border-radius:8px;font-weight:700">ClassMatch</div>'
        '<h2 style="font-size:28px;margin:22px 0 8px">Your lesson is confirmed.</h2>'
        '<p>The available time you selected has been reserved immediately.</p>'
        f'{details(request.get("student_timezone") or "UTC")}<p>We will email you immediately if the lesson is declined, cancelled, or otherwise updated.</p></div>'
    )
    tutor_html = (
        '<div style="font-family:Arial,sans-serif;color:#10253b;line-height:1.55;max-width:620px">'
        '<div style="display:inline-block;padding:7px 11px;background:#315fe7;color:white;border-radius:8px;font-weight:700">ClassMatch</div>'
        '<h2 style="font-size:28px;margin:22px 0 8px">A lesson has been booked.</h2>'
        '<p>A student selected one of your available times, so the lesson was confirmed automatically.</p>'
        f'{details(slot.get("timezone") or "UTC")}<p>We will email you immediately if the lesson is declined, cancelled, or otherwise updated.</p></div>'
    )
    reserver = str(request.get("guardian_email") or "").strip().lower()
    tutor_email = str(tutor.get("tutor_email") or "").strip().lower()
    results = []
    if recipients is None or reserver in recipients:
        results.append(send_email(event_type="session_confirmed_reserver", to=reserver, subject="ClassMatch lesson confirmed", html=reserver_html, related_id=request["id"]))
    if recipients is None or tutor_email in recipients:
        results.append(send_email(event_type="session_confirmed_tutor", to=tutor_email, subject="New ClassMatch lesson booked", html=tutor_html, related_id=request["id"]))
    if not results:
        return True
    return bool(results) and all(results)


def notify_session_status(request: dict[str, Any], recipients: set[str] | None = None) -> bool:
    tutor, slot, status = _record(request.get("tutors")), _record(request.get("availability_slots")), request["status"]
    status_copy = {
        "confirmed": ("Session confirmed", "This lesson is confirmed."),
        "declined": ("Session declined", "This lesson can no longer go ahead. The reserved time has been released."),
        "cancelled": ("Session cancelled", "This lesson has been cancelled and the reserved time has been released."),
        "completed": ("Session completed", "This lesson has been marked as completed."),
    }
    heading, explanation = status_copy.get(status, (f"Session {status}", f"The session status is now {status}."))
    meeting = ""
    if request.get("meeting_url") and status == "confirmed":
        url = escape(request["meeting_url"], quote=True)
        meeting = f"<p><b>Lesson link:</b> <a href=\"{url}\">Open lesson</a></p>"
    def message(timezone_name: str) -> str:
        return (
            '<div style="font-family:Arial,sans-serif;color:#10253b;line-height:1.55;max-width:620px">'
            '<div style="display:inline-block;padding:7px 11px;background:#315fe7;color:white;border-radius:8px;font-weight:700">ClassMatch</div>'
            f"<h2>{escape(heading)}</h2><p>{escape(explanation)}</p>"
            f"<p>{escape(request['student_first_name'])} with {escape(tutor['full_name'])} for {escape(request['subject'])}.</p>"
            f"<p><b>Reserver:</b> {escape(request.get('guardian_name', 'Guardian'))}</p>"
            f"<p><b>Time:</b> {escape(format_slot(slot, timezone_name))}</p>{meeting}"
            "<p>Guardians should remain included in all communication.</p></div>"
        )
    reserver = str(request.get("guardian_email") or "").strip().lower()
    tutor_email = str(tutor.get("tutor_email") or "").strip().lower()
    results = []
    if recipients is None or reserver in recipients:
        results.append(send_email(event_type=f"session_status_{status}_reserver", to=reserver, subject=f"ClassMatch session {status}", html=message(request.get("student_timezone") or "UTC"), related_id=request["id"]))
    if recipients is None or tutor_email in recipients:
        results.append(send_email(event_type=f"session_status_{status}_tutor", to=tutor_email, subject=f"ClassMatch session {status}", html=message(slot.get("timezone") or "UTC"), related_id=request["id"]))
    if not results:
        return True
    return bool(results) and all(results)
