from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import Client, create_client

from core import build_recurring_slots, public_name, valid_timezone, visible_upcoming_requests


class ConfigurationError(RuntimeError):
    pass


def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value).strip()


def configuration_missing() -> list[str]:
    required = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY", "RESEND_API_KEY", "FROM_EMAIL", "COOKIE_PASSWORD")
    return [name for name in required if not secret(name)]


@st.cache_resource
def admin_db() -> Client:
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ConfigurationError("The database connection has not been configured yet.")
    return create_client(url, key)


def user_db(access_token: str) -> Client:
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ConfigurationError("Account access has not been configured yet.")
    client = create_client(url, key)
    client.postgrest.auth(access_token)
    return client


def owner_emails() -> set[str]:
    configured = secret("OWNER_EMAILS") or secret("OWNER_EMAIL", "taleenalali5@gmail.com")
    return {email.strip().lower() for email in configured.replace(";", ",").split(",") if email.strip()}


def require_owner(user: dict[str, Any] | None) -> None:
    if not user or user.get("email", "").lower() not in owner_emails():
        raise PermissionError("Owner access is required.")


def tutor_assignment(user: dict[str, Any] | None) -> dict[str, Any] | None:
    """Resolve a verified signed-in user to the tutor profile assigned by an owner."""
    if not user or not user.get("email"):
        return None
    rows = (
        admin_db().table("tutor_roles")
        .select("id,email,tutor_id,timezone,timezone_confirmed,created_at,tutors(id,full_name,tutor_email,country,active,deleted_at)")
        .eq("email", str(user["email"]).strip().lower()).limit(1).execute().data
    )
    if not rows:
        return None
    assignment = rows[0]
    tutor = assignment.get("tutors") or {}
    if isinstance(tutor, list):
        tutor = tutor[0] if tutor else {}
    return assignment if tutor.get("active") and not tutor.get("deleted_at") else None


def require_tutor(user: dict[str, Any] | None) -> dict[str, Any]:
    assignment = tutor_assignment(user)
    if not assignment:
        raise PermissionError("Tutor access is required.")
    return assignment


def friendly_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "tutors_email_unique" in message or ("duplicate key" in message and "tutor" in message):
        return "A tutor with that email already exists. Edit the existing tutor instead."
    if "no longer available" in message or "duplicate key" in message or "one_active_request" in message:
        return "That lesson time was just taken. Please choose another available time."
    if "too many recent requests" in message:
        return "You have made several recent requests. Please wait an hour before trying again."
    if "jwt expired" in message or "invalid jwt" in message or "token has expired" in message:
        return "Your session expired. Please sign in again."
    if "permission" in message or "row-level security" in message or "not authorized" in message:
        return "Your account does not have permission for that action."
    if "invalid login" in message or "invalid credentials" in message:
        return "The email or password was not accepted."
    if "email not confirmed" in message:
        return "Confirm your email from the message Supabase sent, then sign in."
    if "user already registered" in message:
        return "An account already exists for that email. Sign in or reset its password."
    if "token" in message and ("expired" in message or "invalid" in message):
        return "That reset code is invalid or expired."
    if isinstance(exc, (ValueError, ConfigurationError, PermissionError)):
        return str(exc)
    return "Something went wrong. Please try again. If it continues, email the TM Tutoring owner."


@st.cache_data(ttl=30, show_spinner=False)
def public_tutors(grade: int, subject: str) -> list[dict[str, Any]]:
    rows = (
        admin_db().table("tutors")
        .select("id,full_name,age,school_grade,subjects,languages,min_student_grade,max_student_grade,bio")
        .eq("active", True).is_("deleted_at", "null")
        .lte("min_student_grade", grade).gte("max_student_grade", grade)
        .contains("subjects", [subject]).order("approved_at", desc=True).limit(50).execute().data
    )
    for tutor in rows:
        tutor["full_name"] = public_name(tutor["full_name"])
    return rows


@st.cache_data(ttl=10, show_spinner=False)
def open_slots(tutor_id: str) -> list[dict[str, Any]]:
    return (
        admin_db().table("availability_slots")
        .select("id,starts_at,ends_at,timezone,status").eq("tutor_id", tutor_id)
        .in_("status", ["open", "requested", "booked"])
        .gte("starts_at", datetime.now(timezone.utc).isoformat()).order("starts_at").limit(100).execute().data
    )


@st.cache_data(ttl=10, show_spinner=False)
def open_slot_summaries(tutor_ids: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    if not tutor_ids:
        return {}
    rows = (
        admin_db().table("availability_slots")
        .select("id,tutor_id,starts_at,ends_at,timezone,status")
        .in_("tutor_id", list(tutor_ids)).eq("status", "open")
        .gte("starts_at", datetime.now(timezone.utc).isoformat()).order("starts_at").limit(500).execute().data
    )
    summaries: dict[str, dict[str, Any]] = {}
    for slot in rows:
        summary = summaries.setdefault(str(slot["tutor_id"]), {"count": 0, "next_slot": slot})
        summary["count"] += 1
    return summaries


def request_session(values: dict[str, Any], access_token: str) -> dict[str, Any]:
    response = user_db(access_token).rpc("request_tutoring_session", values).execute()
    open_slots.clear()
    open_slot_summaries.clear()
    request_id = response.data[0] if isinstance(response.data, list) else response.data
    return session_request(str(request_id))


def session_request(request_id: str) -> dict[str, Any]:
    return (
        admin_db().table("session_requests")
        .select("*,tutors(full_name,tutor_email),availability_slots(starts_at,ends_at,timezone)")
        .eq("id", request_id).single().execute().data
    )


def approved_tutors(user: dict[str, Any]) -> list[dict[str, Any]]:
    require_owner(user)
    return admin_db().table("tutors").select("*").eq("active", True).is_("deleted_at", "null").order("full_name").limit(200).execute().data


def managed_tutors(user: dict[str, Any]) -> list[dict[str, Any]]:
    require_owner(user)
    return admin_db().table("tutors").select("*").is_("deleted_at", "null").order("full_name").limit(200).execute().data


def tutor_role_assignments(user: dict[str, Any]) -> list[dict[str, Any]]:
    require_owner(user)
    return (
        admin_db().table("tutor_roles")
        .select("id,email,tutor_id,timezone,timezone_confirmed,created_at,tutors(full_name,country,active,deleted_at)")
        .order("email").limit(200).execute().data
    )


def assign_tutor_role(tutor_id: str, email: str, user: dict[str, Any]) -> None:
    require_owner(user)
    normalized = email.strip().lower()
    if not normalized:
        raise ValueError("Enter the tutor's verified account email.")
    admin_db().rpc(
        "assign_tutor_role",
        {"p_tutor_id": tutor_id, "p_email": normalized, "p_actor_user_id": user.get("id")},
    ).execute()


def remove_tutor_role(role_id: str, user: dict[str, Any]) -> None:
    require_owner(user)
    rows = admin_db().table("tutor_roles").delete().eq("id", role_id).execute().data
    if not rows:
        raise ValueError("That tutor role was not found.")


def add_tutor(values: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    require_owner(user)
    email = str(values.get("tutor_email", "")).strip().lower()
    duplicate = admin_db().table("tutors").select("id").eq("tutor_email", email).limit(1).execute().data
    if duplicate:
        raise ValueError("A tutor with that email already exists. Edit the existing tutor instead.")
    payload = {**values, "tutor_email": email, "active": bool(values.get("active", True))}
    rows = admin_db().table("tutors").insert(payload).execute().data
    if not rows:
        raise RuntimeError("Tutor publishing did not return a saved record.")
    public_tutors.clear()
    open_slot_summaries.clear()
    return rows[0]


def update_tutor(tutor_id: str, values: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    require_owner(user)
    email = str(values.get("tutor_email", "")).strip().lower()
    duplicate = admin_db().table("tutors").select("id").eq("tutor_email", email).neq("id", tutor_id).limit(1).execute().data
    if duplicate:
        raise ValueError("A tutor with that email already exists.")
    rows = admin_db().table("tutors").update({**values, "tutor_email": email}).eq("id", tutor_id).execute().data
    if not rows:
        raise ValueError("That tutor could not be found.")
    public_tutors.clear()
    open_slot_summaries.clear()
    return rows[0]


def delete_tutor(tutor_id: str, user: dict[str, Any]) -> None:
    """Remove a tutor from the app while retaining historical bookings safely."""
    require_owner(user)
    now = datetime.now(timezone.utc).isoformat()
    rows = (
        admin_db().table("tutors")
        .update({"active": False, "deleted_at": now})
        .eq("id", tutor_id).is_("deleted_at", "null").execute().data
    )
    if not rows:
        raise ValueError("That tutor could not be found or was already deleted.")
    admin_db().table("availability_slots").update({"status": "cancelled"}).eq("tutor_id", tutor_id).eq("status", "open").execute()
    public_tutors.clear()
    open_slots.clear()
    open_slot_summaries.clear()


def set_tutor_active(tutor_id: str, active: bool, user: dict[str, Any]) -> None:
    require_owner(user)
    admin_db().table("tutors").update({"active": active}).eq("id", tutor_id).execute()
    public_tutors.clear()
    open_slot_summaries.clear()


def add_recurring_slots(tutor_id: str, first_date: date, weekdays: list[int], weeks: int, window_start: time, window_end: time, lesson_minutes: int, break_minutes: int, timezone_name: str, user: dict[str, Any]) -> int:
    require_owner(user)
    payload = build_recurring_slots(tutor_id, first_date, weekdays, weeks, window_start, window_end, lesson_minutes, break_minutes, timezone_name)
    existing = (
        admin_db().table("availability_slots").select("starts_at").eq("tutor_id", tutor_id)
        .gte("starts_at", payload[0]["starts_at"]).lte("starts_at", payload[-1]["starts_at"]).execute().data
    )
    known = {row["starts_at"] for row in existing}
    new_rows = [row for row in payload if row["starts_at"] not in known]
    if new_rows:
        admin_db().table("availability_slots").insert(new_rows).execute()
        open_slots.clear()
        open_slot_summaries.clear()
    return len(new_rows)


def upcoming_slots(tutor_id: str, user: dict[str, Any]) -> list[dict[str, Any]]:
    require_owner(user)
    return (
        admin_db().table("availability_slots").select("id,starts_at,ends_at,timezone,status")
        .eq("tutor_id", tutor_id).gte("starts_at", datetime.now(timezone.utc).isoformat())
        .order("starts_at").limit(200).execute().data
    )


def cancel_open_slot(slot_id: str, user: dict[str, Any]) -> None:
    require_owner(user)
    updated = admin_db().table("availability_slots").update({"status": "cancelled"}).eq("id", slot_id).eq("status", "open").execute().data
    if not updated:
        raise ValueError("Only an open, unrequested time can be removed.")
    open_slots.clear()
    open_slot_summaries.clear()


def tutor_set_timezone(timezone_name: str, access_token: str, user: dict[str, Any]) -> None:
    assignment = require_tutor(user)
    timezone_name = valid_timezone(timezone_name)
    rows = (
        user_db(access_token).table("tutor_roles").update({"timezone": timezone_name, "timezone_confirmed": True})
        .eq("id", assignment["id"]).execute().data
    )
    if not rows:
        raise PermissionError("Your tutor timezone could not be updated.")


def tutor_add_recurring_slots(tutor_id: str, first_date: date, weekdays: list[int], weeks: int, window_start: time, window_end: time, lesson_minutes: int, break_minutes: int, timezone_name: str, access_token: str, user: dict[str, Any]) -> int:
    assignment = require_tutor(user)
    if str(assignment["tutor_id"]) != str(tutor_id):
        raise PermissionError("Tutors can only manage their own availability.")
    payload = build_recurring_slots(tutor_id, first_date, weekdays, weeks, window_start, window_end, lesson_minutes, break_minutes, timezone_name)
    client = user_db(access_token)
    existing = (
        client.table("availability_slots").select("starts_at").eq("tutor_id", tutor_id)
        .gte("starts_at", payload[0]["starts_at"]).lte("starts_at", payload[-1]["starts_at"]).execute().data
    )
    known = {row["starts_at"] for row in existing}
    new_rows = [row for row in payload if row["starts_at"] not in known]
    if new_rows:
        client.table("availability_slots").insert(new_rows).execute()
        open_slots.clear()
        open_slot_summaries.clear()
    return len(new_rows)


def tutor_slots(access_token: str, user: dict[str, Any]) -> list[dict[str, Any]]:
    assignment = require_tutor(user)
    return (
        user_db(access_token).table("availability_slots")
        .select("id,tutor_id,starts_at,ends_at,timezone,status")
        .eq("tutor_id", assignment["tutor_id"]).order("starts_at").limit(500).execute().data
    )


def tutor_update_open_slot(slot_id: str, slot_date: date, start: time, end: time, timezone_name: str, access_token: str, user: dict[str, Any]) -> None:
    assignment = require_tutor(user)
    timezone_name = valid_timezone(timezone_name)
    zone = ZoneInfo(timezone_name)
    starts_at = datetime.combine(slot_date, start, tzinfo=zone).astimezone(timezone.utc)
    ends_at = datetime.combine(slot_date, end, tzinfo=zone).astimezone(timezone.utc)
    if starts_at <= datetime.now(timezone.utc) or ends_at <= starts_at:
        raise ValueError("Choose a future time with an end after its start.")
    rows = (
        user_db(access_token).table("availability_slots")
        .update({"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat(), "timezone": timezone_name})
        .eq("id", slot_id).eq("tutor_id", assignment["tutor_id"]).eq("status", "open").execute().data
    )
    if not rows:
        raise ValueError("Only your own open times can be edited.")
    open_slots.clear()
    open_slot_summaries.clear()


def tutor_cancel_open_slot(slot_id: str, access_token: str, user: dict[str, Any]) -> None:
    assignment = require_tutor(user)
    rows = (
        user_db(access_token).table("availability_slots").update({"status": "cancelled"})
        .eq("id", slot_id).eq("tutor_id", assignment["tutor_id"]).eq("status", "open").execute().data
    )
    if not rows:
        raise ValueError("Only your own open, unbooked times can be removed.")
    open_slots.clear()
    open_slot_summaries.clear()


def tutor_session_requests(access_token: str, user: dict[str, Any]) -> list[dict[str, Any]]:
    assignment = require_tutor(user)
    return (
        user_db(access_token).table("session_requests")
        .select("id,tutor_id,slot_id,student_first_name,student_grade,subject,guardian_email,notes,status,meeting_url,created_at,student_timezone,availability_slots(starts_at,ends_at,timezone,status)")
        .eq("tutor_id", assignment["tutor_id"]).order("created_at", desc=True).limit(300).execute().data
    )


def all_session_requests(user: dict[str, Any]) -> list[dict[str, Any]]:
    require_owner(user)
    rows = (
        admin_db().table("session_requests")
        .select("*,tutors(full_name,tutor_email),availability_slots(starts_at,ends_at,timezone)")
        .order("created_at", desc=True).limit(300).execute().data
    )
    return visible_upcoming_requests(rows)


def user_session_requests(access_token: str, user_id: str) -> list[dict[str, Any]]:
    rows = (
        user_db(access_token).table("session_requests")
        .select("id,tutor_id,slot_id,student_first_name,subject,status,meeting_url,created_at,student_timezone")
        .eq("requester_user_id", user_id)
        .order("created_at", desc=True).limit(100).execute().data
    )
    if not rows:
        return []
    tutor_ids = list({str(row["tutor_id"]) for row in rows})
    slot_ids = list({str(row["slot_id"]) for row in rows})
    tutors = admin_db().table("tutors").select("id,full_name").in_("id", tutor_ids).execute().data
    slots = admin_db().table("availability_slots").select("id,starts_at,ends_at,timezone").in_("id", slot_ids).execute().data
    tutor_map = {str(item["id"]): item for item in tutors}
    slot_map = {str(item["id"]): item for item in slots}
    for row in rows:
        row["tutors"] = tutor_map.get(str(row["tutor_id"]))
        row["availability_slots"] = slot_map.get(str(row["slot_id"]))
    return visible_upcoming_requests(rows)


def change_session_status(request_id: str, status: str, meeting_url: str, user: dict[str, Any]) -> dict[str, Any]:
    require_owner(user)
    response = admin_db().rpc("change_session_status", {"p_request_id": request_id, "p_status": status, "p_meeting_url": meeting_url or None}).execute()
    open_slots.clear()
    open_slot_summaries.clear()
    result_id = response.data[0] if isinstance(response.data, list) else response.data
    return session_request(str(result_id))


def log_email(event_type: str, recipient: str, subject: str, status: str, provider_id: str = "", error: str = "", related_id: str = "") -> None:
    try:
        admin_db().table("email_events").insert({"event_type": event_type, "recipient": recipient, "subject": subject, "status": status, "provider_message_id": provider_id or None, "error": error or None, "related_id": related_id or None}).execute()
    except Exception:
        return
