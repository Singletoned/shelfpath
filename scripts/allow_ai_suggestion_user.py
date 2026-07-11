from __future__ import annotations

import os
import sys

import httpx


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/allow_ai_suggestion_user.py email@example.com")
    email = sys.argv[1].strip().lower()
    if not email:
        raise SystemExit("Email address is required.")
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    service_role_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    response = httpx.post(
        f"{supabase_url}/rest/v1/ai_series_suggestion_allowed_users?on_conflict=email",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        json={"email": email},
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Supabase allow-list request failed: {response.status_code} {response.text}"
        )
    print(f"Allowed AI series suggestions for {email}")


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
