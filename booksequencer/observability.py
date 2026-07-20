from __future__ import annotations

import sentry_sdk

from booksequencer.config import Settings


def configure_sentry(settings: Settings) -> None:
    """Enable Sentry only when this deployment has been configured with a DSN."""
    if settings.sentry_dsn is None:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
    )
