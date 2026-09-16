from __future__ import annotations

from html import escape
from typing import Any

import resend

from backend import log_email, secret
from core import format_slot


def send_email(*, event_type: str, to: str, subject: str, html: str, related_id: str = "") -> bool:
    api_key, sender = secret("RESEND_API_KEY"), secret("FROM_EMAIL")
    if not api_key or not sender:
        log_email(event_type, to, subject, "failed", error="Resend is not configured", related_id=related_id)
        return False
    resend.api_key = api_key
    try:
        result = resend.Emails.send({"from": sender, "to": [to], "subject": subject, "html": html})
        provider_id = result.get("id", "") if isinstance(result, dict) else str(getattr(result, "id", ""))
        log_email(event_type, to, subject, "sent", provider_id=provider_id, related_id=related_id)
        return True
    except Exception as exc:
        log_email(event_type, to, subject, "failed", error=str(exc)[:500], related_id=related_id)
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


def notify_session_request(request: dict[str, Any]) -> bool:
    tutor, slot = request["tutors"], request["availability_slots"]
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
            f'<p style="margin:0 0 8px"><b>Status:</b> Requested — waiting for approval</p>'
            f'<p style="margin:0"><b>Learning notes:</b> {notes}</p></div>'
        )
    reserver_html = (
        '<div style="font-family:Arial,sans-serif;color:#10253b;line-height:1.55;max-width:620px">'
        '<div style="display:inline-block;padding:7px 11px;background:#315fe7;color:white;border-radius:8px;font-weight:700">TM Tutoring</div>'
        '<h2 style="font-size:28px;margin:22px 0 8px">We received your lesson request.</h2>'
        '<p>Your reservation has been saved and the selected time is now pending. It is not confirmed yet.</p>'
        f'{details(request.get("student_timezone") or "UTC")}<p>The TM Tutoring owner will review the request. We will email you again when its status changes.</p></div>'
    )
    tutor_html = (
        '<div style="font-family:Arial,sans-serif;color:#10253b;line-height:1.55;max-width:620px">'
        '<div style="display:inline-block;padding:7px 11px;background:#315fe7;color:white;border-radius:8px;font-weight:700">TM Tutoring</div>'
        '<h2 style="font-size:28px;margin:22px 0 8px">You have a new lesson request.</h2>'
        '<p>A student has requested one of your available times. The request is waiting for owner approval and is not confirmed yet.</p>'
        f'{details(slot.get("timezone") or "UTC")}<p>Please wait for the confirmation update before treating the lesson as booked.</p></div>'
    )
    results = [
        send_email(event_type="session_requested_reserver", to=request["guardian_email"].strip().lower(), subject="TM Tutoring request received", html=reserver_html, related_id=request["id"]),
        send_email(event_type="session_requested_tutor", to=tutor["tutor_email"].strip().lower(), subject="New TM Tutoring lesson request", html=tutor_html, related_id=request["id"]),
    ]
    return bool(results) and all(results)


def notify_session_status(request: dict[str, Any]) -> bool:
    tutor, slot, status = request["tutors"], request["availability_slots"], request["status"]
    meeting = ""
    if request.get("meeting_url") and status == "confirmed":
        url = escape(request["meeting_url"], quote=True)
        meeting = f"<p><b>Lesson link:</b> <a href=\"{url}\">Open lesson</a></p>"
    html = (
        f"<h2>Session {escape(status)}</h2>"
        f"<p>{escape(request['student_first_name'])} with {escape(tutor['full_name'])} for {escape(request['subject'])}.</p>"
        f"<p><b>Reserver:</b> {escape(request.get('guardian_name', 'Guardian'))}</p>"
        f"<p><b>Time:</b> {escape(format_slot(slot))}</p>{meeting}"
        "<p>Guardians should remain included in all communication.</p>"
    )
    results = [send_email(event_type=f"session_{status}", to=email, subject=f"TM Tutoring session {status}", html=html, related_id=request["id"]) for email in _recipients(request)]
    return bool(results) and all(results)
