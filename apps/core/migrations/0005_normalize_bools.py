"""Data migration to normalize bool SystemConfig values to lowercase.

Converts: True -> true, FALSE -> false, Yes -> true, No -> false, etc.
"""

from django.db import migrations


def normalize_bools_forward(model_or_apps, schema_editor=None):
    """Normalize bool values. Can be called with model class directly (tests)
    or via RunPython (apps, schema_editor).
    """
    # Support both direct model class and apps registry
    if hasattr(model_or_apps, 'objects'):
        SystemConfig = model_or_apps
    else:
        SystemConfig = model_or_apps.get_model("core", "SystemConfig")

    TRUTHY = {"true", "1", "yes"}
    FALSY = {"false", "0", "no"}

    for cfg in SystemConfig.objects.filter(value_type="bool"):
        lower = cfg.value.strip().lower()
        if lower in TRUTHY:
            cfg.value = "true"
        elif lower in FALSY:
            cfg.value = "false"
        else:
            # Unknown value, leave as-is
            continue
        cfg.save(update_fields=["value"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_seed_email_notifications_flag"),
    ]

    operations = [
        migrations.RunPython(
            normalize_bools_forward,
            migrations.RunPython.noop,
        ),
    ]
