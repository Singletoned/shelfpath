from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_DIR / "data"
DEFAULT_TEMPLATE_DIR = PROJECT_DIR / "templates"


@dataclass(frozen=True)
class Settings:
    storage: str
    data_dir: Path
    supabase_url: str | None
    supabase_publishable_key: str | None
    session_secret: str
    debug: bool


def load_settings() -> Settings:
    return Settings(
        storage=os.environ.get("SHELFPATH_STORAGE", "file"),
        data_dir=Path(os.environ.get("SHELFPATH_DATA_DIR", DEFAULT_DATA_DIR)),
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_publishable_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY"),
        session_secret=os.environ.get("SHELFPATH_SESSION_SECRET", "development-only-change-me"),
        debug=os.environ.get("SHELFPATH_DEBUG", "true").lower() == "true",
    )
