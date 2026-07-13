from __future__ import annotations

import os

import httpx


def main() -> None:
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    service_role_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    email = _required_env("SHELFPATH_LOCAL_AUTH_EMAIL").strip().lower()
    password = _required_env("SHELFPATH_LOCAL_AUTH_PASSWORD")
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=20, headers=headers) as client:
        if _user_exists(client, supabase_url, email):
            print(f"Local Supabase auth user already exists: {email}")
            return
        response = client.post(
            f"{supabase_url}/auth/v1/admin/users",
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"name": "Local Shelfpath Tester"},
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Local auth user creation failed: {response.status_code} {response.text}"
        )
    print(f"Created local Supabase auth user: {email}")


def _user_exists(client: httpx.Client, supabase_url: str, email: str) -> bool:
    response = client.get(f"{supabase_url}/auth/v1/admin/users?page=1&per_page=1000")
    if response.status_code >= 400:
        raise RuntimeError(f"Local auth user lookup failed: {response.status_code} {response.text}")
    users = response.json().get("users", [])
    return any(user.get("email", "").lower() == email for user in users)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
