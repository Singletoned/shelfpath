from __future__ import annotations

import unittest
from unittest.mock import patch

from booksequencer.invitations import (
    InvitationTokenError,
    create_invitation_token,
    verify_invitation_token,
)


class InvitationTokenTests(unittest.TestCase):
    def test_token_accepts_the_invited_email_and_claims(self):
        with patch("booksequencer.invitations.time.time", return_value=1_000_000):
            token = create_invitation_token(
                "00000000-0000-0000-0000-000000000001",
                "Reader@Example.test",
                "editor",
                "test-secret",
            )
            claims = verify_invitation_token(
                "00000000-0000-0000-0000-000000000001",
                "reader@example.test",
                "editor",
                token,
                "test-secret",
            )

        self.assertEqual(claims.recipient_email, "reader@example.test")
        self.assertEqual(claims.role, "editor")

    def test_token_rejects_a_different_recipient(self):
        with patch("booksequencer.invitations.time.time", return_value=1_000_000):
            token = create_invitation_token(
                "list-id", "reader@example.test", "viewer", "test-secret"
            )
            with self.assertRaisesRegex(InvitationTokenError, "invalid"):
                verify_invitation_token(
                    "list-id", "other@example.test", "viewer", token, "test-secret"
                )

    def test_token_rejects_expiry(self):
        with patch("booksequencer.invitations.time.time", return_value=1_000_000):
            token = create_invitation_token(
                "list-id", "reader@example.test", "viewer", "test-secret"
            )
        with patch("booksequencer.invitations.time.time", return_value=1_000_000 + 604_801):
            with self.assertRaisesRegex(InvitationTokenError, "expired"):
                verify_invitation_token(
                    "list-id", "reader@example.test", "viewer", token, "test-secret"
                )
