from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import create_client

from backend import owner_emails, secret


def _client():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Account sign-in has not been configured yet.")
    return create_client(url, key)


def sign_up(email: str, password: str) -> None:
    """Create an account without starting an unverified app session."""
    _client().auth.sign_up({"email": email.strip().lower(), "password": password})


def sign_in(email: str, password: str) -> dict[str, str]:
    client = _client()
    response = client.auth.sign_in_with_password({"email": email.strip().lower(), "password": password})
    if not response.session or not response.user:
        raise ValueError("The email or password was not accepted.")
    if not (getattr(response.user, "email_confirmed_at", None) or getattr(response.user, "confirmed_at", None)):
        client.auth.sign_out()
        raise ValueError("Confirm your email from the message Supabase sent, then sign in.")
    _save_session(response.session)
    return {"id": str(response.user.id), "email": str(response.user.email).lower()}


def send_password_code(email: str) -> None:
    _client().auth.reset_password_email(email.strip().lower())


def reset_password_with_code(email: str, code: str, new_password: str) -> None:
    client = _client()
    response = client.auth.verify_otp({"email": email.strip().lower(), "token": code.strip(), "type": "recovery"})
    if not response.session:
        raise ValueError("That reset code is invalid or expired.")
    client.auth.set_session(response.session.access_token, response.session.refresh_token)
    client.auth.update_user({"password": new_password})
    client.auth.sign_out()


def current_user() -> dict[str, str] | None:
    access = st.session_state.get("auth_access_token")
    refresh = st.session_state.get("auth_refresh_token")
    if not access or not refresh:
        return None
    try:
        response = _client().auth.set_session(access, refresh)
        if not response.user or not response.session:
            sign_out()
            return None
        if not (getattr(response.user, "email_confirmed_at", None) or getattr(response.user, "confirmed_at", None)):
            sign_out()
            return None
        _save_session(response.session)
        return {"id": str(response.user.id), "email": str(response.user.email).lower()}
    except Exception:
        sign_out()
        return None


def access_token() -> str:
    token = st.session_state.get("auth_access_token")
    if not token:
        raise PermissionError("Please sign in again.")
    return str(token)


def sign_out() -> None:
    st.session_state.pop("auth_access_token", None)
    st.session_state.pop("auth_refresh_token", None)


def is_owner(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("email", "").lower() in owner_emails())


def _save_session(session: Any) -> None:
    st.session_state.auth_access_token = session.access_token
    st.session_state.auth_refresh_token = session.refresh_token
