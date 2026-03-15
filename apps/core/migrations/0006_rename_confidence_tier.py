"""Rename auto_assign_confidence_threshold -> auto_assign_confidence_tier.

The old key name implied a numeric threshold but actually stores an exact
confidence tier string like "HIGH". Rename for clarity.
"""

from django.db import migrations


def rename_key_forward(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.filter(key="auto_assign_confidence_threshold").update(
        key="auto_assign_confidence_tier"
    )


def rename_key_reverse(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.filter(key="auto_assign_confidence_tier").update(
        key="auto_assign_confidence_threshold"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_normalize_bools"),
    ]

    operations = [
        migrations.RunPython(rename_key_forward, rename_key_reverse),
    ]
