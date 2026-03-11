"""Seed operating_mode config entry — defaults to 'off' for dev safety."""

from django.db import migrations


def seed_operating_mode(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.update_or_create(
        key="operating_mode",
        defaults={
            "value": "off",
            "value_type": "str",
            "category": "feature_flags",
            "description": "Pipeline operating mode (off/dev/production)",
        },
    )


def unseed_operating_mode(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.filter(key="operating_mode").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_seed_default_config"),
    ]

    operations = [
        migrations.RunPython(seed_operating_mode, unseed_operating_mode),
    ]
