from __future__ import annotations

import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass(frozen=True)
class InvitationEmailSender:
    host: str
    port: int
    username: str | None
    password: str | None
    sender: str

    async def send_list_invitation(
        self, recipient: str, list_name: str, role: str, invitation_url: str
    ) -> None:
        message = _invitation_message(recipient, list_name, role, invitation_url, self.sender)
        await asyncio.to_thread(_send, self.host, self.port, self.username, self.password, message)


def _invitation_message(
    recipient: str, list_name: str, role: str, login_url: str, sender: str
) -> EmailMessage:
    access = "update" if role == "editor" else "view"
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = f"You were invited to {list_name} on Shelfpath"
    message.set_content(
        f"You were invited to {access} the Shelfpath list {list_name}.\n\n"
        f"Open this invitation and sign in with this email address:\n{login_url}\n\n"
        "If you are new to Shelfpath, the sign-in link will create your account and add the list."
    )
    return message


def _send(
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    message: EmailMessage,
) -> None:
    with smtplib.SMTP(host, port, timeout=20) as client:
        if username is not None:
            if password is None:
                raise ValueError(
                    "SHELFPATH_SMTP_PASSWORD is required with SHELFPATH_SMTP_USERNAME."
                )
            client.starttls()
            client.login(username, password)
        client.send_message(message)
