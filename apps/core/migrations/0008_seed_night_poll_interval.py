"""Seed night_poll_interval_minutes SystemConfig key.

During quiet hours (8 PM - 8 AM IST), polling slows from 5min to 15min
to reduce API calls and resources when the team is offline.
"""

from django.db import migrations


def seed_night_poll_interval(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.update_or_create(
        key="night_poll_interval_minutes",
        defaults={
            "value": "15",
            "value_type": "INT",
            "description": "Gmail poll interval during quiet hours (8 PM - 8 AM IST)",
            "category": "scheduler",
        },
    )


def remove_night_poll_interval(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.filter(key="night_poll_interval_minutes").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_seed_alert_config"),
    ]

    operations = [
        migrations.RunPython(seed_night_poll_interval, remove_night_poll_interval),
    ]
