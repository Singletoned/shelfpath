from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient


class ClerkAuthenticationError(ValueError):
    """Raised when Clerk does not accept a browser session token."""


@dataclass(frozen=True)
class ClerkConfiguration:
    issuer: str
    authorized_party: str


def verify_clerk_session(token: str, configuration: ClerkConfiguration) -> dict[str, Any]:
    """Verify a Clerk session JWT and return Shelfpath's minimal session identity."""
    jwks = PyJWKClient(f"{configuration.issuer.rstrip('/')}/.well-known/jwks.json")
    try:
        signing_key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=None,
            issuer=configuration.issuer,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as error:
        raise ClerkAuthenticationError("Clerk session token verification failed.") from error
    authorized_party = claims.get("azp")
    if authorized_party != configuration.authorized_party:
        raise ClerkAuthenticationError("Clerk session token has an unexpected authorized party.")
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ClerkAuthenticationError("Clerk session token does not contain a user id.")
    email = claims.get("email")
    if email is not None and not isinstance(email, str):
        raise ClerkAuthenticationError("Clerk session token has an invalid email claim.")
    return {"id": user_id, "email": email}


async def load_clerk_user(user: dict[str, Any], secret_key: str) -> dict[str, Any]:
    """Load the primary email from Clerk when the session JWT omits it."""
    if user.get("email"):
        return user
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"https://api.clerk.com/v1/users/{user['id']}",
            headers={"Authorization": f"Bearer {secret_key}"},
        )
    if response.status_code >= 400:
        raise ClerkAuthenticationError(
            f"Clerk user lookup failed: {response.status_code} {response.text}"
        )
    payload = response.json()
    primary_id = payload.get("primary_email_address_id")
    emails = payload.get("email_addresses", [])
    email = next(
        (item.get("email_address") for item in emails if item.get("id") == primary_id), None
    )
    if not isinstance(email, str) or not email:
        raise ClerkAuthenticationError("Clerk user does not have a primary email address.")
    return {"id": user["id"], "email": email}
