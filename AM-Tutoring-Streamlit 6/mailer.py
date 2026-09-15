from __future__ import annotations

from html import escape
from typing import Any

import resend

from backend import log_email, secret
from core import format_slot


def send_email(*, event_type: str, to: str, subject: str, html: str, related_id: str = "") -> bool:
    api_key, sender = secret("RESEND_API_KEY"), secret("FROM_EMAIL")
    if not api_key or not sender:
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
    html = (
        "<h2>New tutoring request</h2>"
        f"<p><b>Student:</b> {escape(request['student_first_name'])}</p>"
        f"<p><b>Reserver:</b> {escape(request.get('guardian_name', 'Guardian'))}</p>"
        f"<p><b>Tutor:</b> {escape(tutor['full_name'])}</p>"
        f"<p><b>Subject / grade:</b> {escape(request['subject'])} / {request['student_grade']}</p>"
        f"<p><b>Requested time:</b> {escape(format_slot(slot))}</p>"
        "<p>The AM Tutoring owner will confirm or decline this request.</p>"
    )
    results = [send_email(event_type="session_requested", to=email, subject="New AM Tutoring session request", html=html, related_id=request["id"]) for email in _recipients(request)]
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
    results = [send_email(event_type=f"session_{status}", to=email, subject=f"AM Tutoring session {status}", html=html, related_id=request["id"]) for email in _recipients(request)]
    return bool(results) and all(results)
