"""Management command to switch the email pipeline operating mode.

Usage:
    python manage.py set_mode              # Show current mode + config
    python manage.py set_mode off          # Everything disabled: no Gmail, no AI, no Chat
    python manage.py set_mode dev          # Local dev: info@ inbox, real AI, no Chat
    python manage.py set_mode production   # Full pipeline: everything enabled
"""

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import SystemConfig

MODE_CONFIGS = {
    "off": {
        "operating_mode": ("off", "str"),
        "ai_triage_enabled": ("false", "bool"),
        "chat_notifications_enabled": ("false", "bool"),
        "monitored_inboxes": ("", "str"),
    },
    "dev": {
        "operating_mode": ("dev", "str"),
        "ai_triage_enabled": ("true", "bool"),
        "chat_notifications_enabled": ("false", "bool"),
        "monitored_inboxes": ("info@vidarbhainfotech.com", "str"),
    },
    "production": {
        "operating_mode": ("production", "str"),
        "ai_triage_enabled": ("true", "bool"),
        "chat_notifications_enabled": ("true", "bool"),
        "monitored_inboxes": (
            "info@vidarbhainfotech.com,sales@vidarbhainfotech.com",
            "str",
        ),
    },
}

# Keys to display in the status table
DISPLAY_KEYS = [
    "operating_mode",
    "ai_triage_enabled",
    "chat_notifications_enabled",
    "monitored_inboxes",
]


class Command(BaseCommand):
    help = "Switch pipeline operating mode (off/dev/production) or show current mode."

    def add_arguments(self, parser):
        parser.add_argument(
            "mode",
            nargs="?",
            choices=list(MODE_CONFIGS.keys()),
            help="Target mode: off, dev, or production. Omit to show current mode.",
        )

    def handle(self, *args, **options):
        mode = options["mode"]

        if mode is None:
            self._show_current()
        else:
            self._set_mode(mode)

    def _set_mode(self, mode):
        """Set all config entries for the given mode atomically."""
        config = MODE_CONFIGS[mode]
        for key, (value, value_type) in config.items():
            SystemConfig.objects.update_or_create(
                key=key,
                defaults={
                    "value": value,
                    "value_type": value_type,
                    "category": "feature_flags" if key != "monitored_inboxes" else "polling",
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Mode set to: {mode}"))
        self.stdout.write("")
        self._show_current()

    def _show_current(self):
        """Print current mode and relevant config values."""
        current_mode = SystemConfig.get("operating_mode", "unknown")

        # Determine style for mode display
        mode_styles = {
            "off": self.style.SUCCESS,
            "dev": self.style.WARNING,
            "production": self.style.ERROR,
        }
        style_fn = mode_styles.get(current_mode, self.style.NOTICE)
        self.stdout.write(f"Current mode: {style_fn(current_mode)}")
        self.stdout.write("")

        # Table header
        self.stdout.write(f"  {'Key':<35} {'Value':<50} {'Type'}")
        self.stdout.write(f"  {'─' * 35} {'─' * 50} {'─' * 6}")

        for key in DISPLAY_KEYS:
            try:
                obj = SystemConfig.objects.get(key=key)
                value = obj.value or "(empty)"
                vtype = obj.value_type
            except SystemConfig.DoesNotExist:
                value = "(not set)"
                vtype = "-"
            self.stdout.write(f"  {key:<35} {value:<50} {vtype}")
