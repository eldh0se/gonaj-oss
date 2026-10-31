"""Cross-cutting endpoints (API root today, shared concerns later)."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        # Register the uncaught-exception triage receiver (007).
        from . import error_signals  # noqa: F401
