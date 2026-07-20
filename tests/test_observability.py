from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from booksequencer.observability import configure_sentry


class SentryConfigurationTests(TestCase):
    def test_configures_sentry_when_a_dsn_is_present(self) -> None:
        settings = SimpleNamespace(
            sentry_dsn="https://public@example.ingest.sentry.io/1",
            sentry_environment="test",
        )
        with patch("booksequencer.observability.sentry_sdk.init") as initialize:
            configure_sentry(settings)
        initialize.assert_called_once_with(
            dsn="https://public@example.ingest.sentry.io/1", environment="test"
        )

    def test_does_not_configure_sentry_without_a_dsn(self) -> None:
        settings = SimpleNamespace(sentry_dsn=None, sentry_environment="test")
        with patch("booksequencer.observability.sentry_sdk.init") as initialize:
            configure_sentry(settings)
        initialize.assert_not_called()
