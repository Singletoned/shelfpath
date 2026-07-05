from __future__ import annotations

from typing import Any

import httpx
from starlette.requests import Request
from starlette.responses import RedirectResponse

HTTP_SEE_OTHER = 303


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


async def verify_supabase_token(
    supabase_url: str,
    publishable_key: str,
    access_token: str,
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
    email = payload.get("email")
    user_id = payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise AuthenticationError("Supabase user response did not include an id.")
    return {"id": user_id, "email": email, "access_token": access_token}
