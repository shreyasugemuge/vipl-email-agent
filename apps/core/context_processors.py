"""
Context processors for VIPL Email Agent.
Provides version and operating mode to all templates.
"""

from django.conf import settings


def vipl_context(request):
    """Inject app version and operating mode into every template context."""
    # Import here to avoid circular imports and allow graceful failure
    try:
        from apps.core.models import SystemConfig

        operating_mode = SystemConfig.get("operating_mode", "off")
    except Exception:
        operating_mode = "off"

    return {
        "app_version": settings.APP_VERSION,
        "operating_mode": operating_mode,
    }
