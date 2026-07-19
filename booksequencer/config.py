from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from booksequencer.ai_series import DEFAULT_OPENAI_MODEL

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_DIR / "data"
DEFAULT_TEMPLATE_DIR = PROJECT_DIR / "templates"
DEFAULT_SUPABASE_URL = "https://pkrxfruhnjsifclnhjyc.supabase.co"


@dataclass(frozen=True)
class Settings:
    storage: str
    data_dir: Path
    supabase_url: str | None
    supabase_publishable_key: str | None
    session_secret: str
    debug: bool
    openai_api_key: str | None
    openai_model: str
    local_auth_email: str | None
    local_auth_password: str | None
    supabase_service_role_key: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    mail_from: str
    public_url: str
    invitation_token_secret: str | None


def load_settings() -> Settings:
    supabase_url = os.environ.get("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get(
        "SUPABASE_ANON_KEY"
    )
    return Settings(
        storage=os.environ.get("SHELFPATH_STORAGE", _default_storage(publishable_key)),
        data_dir=Path(os.environ.get("SHELFPATH_DATA_DIR", DEFAULT_DATA_DIR)),
        supabase_url=supabase_url,
        supabase_publishable_key=publishable_key,
        session_secret=os.environ.get("SHELFPATH_SESSION_SECRET", "development-only-change-me"),
        debug=os.environ.get("SHELFPATH_DEBUG", _default_debug()).lower() == "true",
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        openai_model=os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        local_auth_email=_optional_env("SHELFPATH_LOCAL_AUTH_EMAIL"),
        local_auth_password=_optional_env("SHELFPATH_LOCAL_AUTH_PASSWORD"),
        supabase_service_role_key=_optional_env("SUPABASE_SERVICE_ROLE_KEY"),
        smtp_host=_optional_env("SHELFPATH_SMTP_HOST"),
        smtp_port=int(os.environ.get("SHELFPATH_SMTP_PORT", "1025")),
        smtp_username=_optional_env("SHELFPATH_SMTP_USERNAME"),
        smtp_password=_optional_env("SHELFPATH_SMTP_PASSWORD"),
        mail_from=os.environ.get("SHELFPATH_MAIL_FROM", "Shelfpath <noreply@shelfpath.app>"),
        public_url=os.environ.get("SHELFPATH_PUBLIC_URL", "https://shelfpath.app"),
        invitation_token_secret=_optional_env("SHELFPATH_INVITATION_TOKEN_SECRET"),
    )


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value


def _default_storage(publishable_key: str | None) -> str:
    if publishable_key:
        return "supabase"
    return "file"


def _default_debug() -> str:
    if os.environ.get("RENDER"):
        return "false"
    return "true"
