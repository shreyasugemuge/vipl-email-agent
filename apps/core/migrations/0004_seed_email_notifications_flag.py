from django.db import migrations


def seed_email_notifications_flag(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.update_or_create(
        key="email_notifications_enabled",
        defaults={
            "value": "false",
            "value_type": "bool",
            "category": "feature_flags",
            "description": "Enable/disable email notifications for assignments (requires SMTP config)",
        },
    )


def unseed(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    SystemConfig.objects.filter(key="email_notifications_enabled").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_seed_operating_mode"),
    ]

    operations = [
        migrations.RunPython(seed_email_notifications_flag, unseed),
    ]
