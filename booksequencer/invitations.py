from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

INVITATION_TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
INVITATION_TOKEN_FUTURE_TOLERANCE_SECONDS = 60
TOKEN_PURPOSE = "shelfpath.shared-list-invitation.v1"


class InvitationTokenError(ValueError):
    """Raised when an invitation token cannot be accepted."""


@dataclass(frozen=True)
class InvitationClaims:
    list_id: str
    role: str
    recipient_email: str


def create_invitation_token(list_id: str, recipient_email: str, role: str, secret: str) -> str:
    _validate_role(role)
    timestamp = int(time.time())
    nonce = secrets.token_urlsafe(16)
    signature = _signature(list_id, recipient_email, role, timestamp, nonce, secret)
    return f"{timestamp}.{nonce}.{signature}"


def verify_invitation_token(
    list_id: str, recipient_email: str, role: str, token: str, secret: str
) -> InvitationClaims:
    _validate_role(role)
    timestamp, nonce, provided_signature = _parse_token(token)
    now = int(time.time())
    if timestamp > now + INVITATION_TOKEN_FUTURE_TOLERANCE_SECONDS:
        raise InvitationTokenError("Invitation link is not valid yet.")
    if now - timestamp > INVITATION_TOKEN_MAX_AGE_SECONDS:
        raise InvitationTokenError("Invitation link has expired.")
    expected_signature = _signature(list_id, recipient_email, role, timestamp, nonce, secret)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise InvitationTokenError("Invitation link is invalid.")
    return InvitationClaims(list_id=list_id, role=role, recipient_email=recipient_email)


def _parse_token(token: str) -> tuple[int, str, str]:
    try:
        timestamp_text, nonce, signature = token.split(".")
        timestamp = int(timestamp_text)
    except ValueError as error:
        raise InvitationTokenError("Invitation link is invalid.") from error
    if timestamp < 0 or not nonce or not signature:
        raise InvitationTokenError("Invitation link is invalid.")
    return timestamp, nonce, signature


def _signature(
    list_id: str, recipient_email: str, role: str, timestamp: int, nonce: str, secret: str
) -> str:
    payload = "\x1f".join(
        (TOKEN_PURPOSE, list_id, recipient_email.strip().lower(), role, str(timestamp), nonce)
    ).encode()
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _validate_role(role: str) -> None:
    if role not in {"editor", "viewer"}:
        raise ValueError("Invitation role must be editor or viewer.")
