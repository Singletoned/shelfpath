from __future__ import annotations

from dataclasses import dataclass

import httpx

DEFAULT_RESEND_API_URL = "https://api.resend.com"


@dataclass(frozen=True)
class InvitationEmailSender:
    api_key: str
    sender: str
    api_url: str = DEFAULT_RESEND_API_URL

    async def send_list_invitation(
        self, recipient: str, list_name: str, role: str, invitation_url: str
    ) -> None:
        access = "update" if role == "editor" else "view"
        subject = f"You were invited to {list_name} on Shelfpath"
        text = (
            f"You were invited to {access} the Shelfpath list {list_name}.\n\n"
            f"Open this invitation and sign in with this email address:\n{invitation_url}\n\n"
            "If you are new to Shelfpath, the sign-in link will create your account "
            "and add the list."
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.api_url.rstrip('/')}/emails",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"from": self.sender, "to": [recipient], "subject": subject, "text": text},
            )
        if response.is_error:
            raise RuntimeError(
                f"Resend invitation email failed: {response.status_code} {response.text}"
            )
