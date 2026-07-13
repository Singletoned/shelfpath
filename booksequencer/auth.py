from __future__ import annotations

import time
from typing import Any

import httpx
from starlette.requests import Request
from starlette.responses import RedirectResponse

HTTP_SEE_OTHER = 303
TOKEN_REFRESH_MARGIN_SECONDS = 60


class AuthenticationError(ValueError):
    """Raised when Supabase does not accept an access token."""


def current_user(request: Request) -> dict[str, Any] | None:
    return request.session.get("user")


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise AuthenticationError("Authentication is required.")
    return user


def redirect_to_login(request: Request) -> RedirectResponse:
    return RedirectResponse(f"/login?next={request.url.path}", status_code=HTTP_SEE_OTHER)


async def fresh_user(
    request: Request,
    supabase_url: str | None,
    publishable_key: str | None,
) -> dict[str, Any] | None:
    user = current_user(request)
    if user is None:
        return None
    if not supabase_url or not publishable_key:
        return user
    if user.get("local_auth") is True:
        return user
    if not user.get("refresh_token"):
        request.session.clear()
        return None
    expires_at = user.get("expires_at")
    if (
        isinstance(expires_at, int | float)
        and expires_at > time.time() + TOKEN_REFRESH_MARGIN_SECONDS
    ):
        return user
    try:
        refreshed = await refresh_supabase_session(
            supabase_url,
            publishable_key,
            user["refresh_token"],
        )
    except AuthenticationError:
        request.session.clear()
        return None
    request.session["user"] = refreshed
    return refreshed


async def verify_supabase_token(
    supabase_url: str,
    publishable_key: str,
    access_token: str,
    refresh_token: str,
    expires_at: int | None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
        )
    if response.status_code != 200:
        raise AuthenticationError(response.text)
    payload = response.json()
    return _session_user(payload, access_token, refresh_token, expires_at)


async def refresh_supabase_session(
    supabase_url: str,
    publishable_key: str,
    refresh_token: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": publishable_key},
            json={"refresh_token": refresh_token},
        )
    if response.status_code != 200:
        raise AuthenticationError(response.text)
    payload = response.json()
    user = payload.get("user")
    if not isinstance(user, dict):
        raise AuthenticationError("Supabase refresh response did not include a user.")
    new_refresh_token = payload.get("refresh_token")
    new_access_token = payload.get("access_token")
    if not isinstance(new_refresh_token, str) or not isinstance(new_access_token, str):
        raise AuthenticationError("Supabase refresh response did not include tokens.")
    return _session_user(user, new_access_token, new_refresh_token, payload.get("expires_at"))


def _session_user(
    payload: dict[str, Any],
    access_token: str,
    refresh_token: str,
    expires_at: int | None,
) -> dict[str, Any]:
    email = payload.get("email")
    user_id = payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise AuthenticationError("Supabase user response did not include an id.")
    return {
        "id": user_id,
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }
