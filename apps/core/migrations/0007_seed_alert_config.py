"""Seed SystemConfig keys for unassigned alert system."""

from django.db import migrations


def seed_alert_config(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")

    alert_configs = [
        {
            "key": "unassigned_alert_threshold",
            "value": "5",
            "value_type": "int",
            "category": "alerts",
            "description": "Chat alert fires when unassigned count reaches this number (0 to disable)",
        },
        {
            "key": "unassigned_alert_cooldown_minutes",
            "value": "30",
            "value_type": "int",
            "category": "alerts",
            "description": "Minimum minutes between repeated alerts",
        },
        {
            "key": "_unassigned_was_below_threshold",
            "value": "true",
            "value_type": "str",
            "category": "alerts",
            "description": "Internal: rising-edge tracking flag",
        },
        {
            "key": "last_unassigned_alert_at",
            "value": "",
            "value_type": "str",
            "category": "alerts",
            "description": "Internal: timestamp of last alert",
        },
    ]

    for cfg in alert_configs:
        SystemConfig.objects.update_or_create(
            key=cfg["key"],
            defaults=cfg,
        )


def reverse_alert_config(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.filter(
        key__in=[
            "unassigned_alert_threshold",
            "unassigned_alert_cooldown_minutes",
            "_unassigned_was_below_threshold",
            "last_unassigned_alert_at",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_rename_confidence_tier"),
    ]

    operations = [
        migrations.RunPython(seed_alert_config, reverse_alert_config),
    ]
