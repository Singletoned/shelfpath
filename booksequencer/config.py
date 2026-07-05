from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
    )


def _default_storage(publishable_key: str | None) -> str:
    if publishable_key:
        return "supabase"
    return "file"


def _default_debug() -> str:
    if os.environ.get("RENDER"):
        return "false"
    return "true"
