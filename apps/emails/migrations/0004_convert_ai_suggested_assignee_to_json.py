"""Data migration: convert ai_suggested_assignee from string to JSON-compatible value.

Existing values are plain strings like "Aniket". This converts them to
JSON strings like '{"name": "Aniket"}' or '{}' for empty values,
preparing for the schema migration that changes the field to JSONField.
"""

from django.db import migrations


def convert_assignee_to_json(apps, schema_editor):
    """Convert plain string values to JSON-formatted strings."""
    import json

    Email = apps.get_model("emails", "Email")
    for email in Email.objects.all():
        old_val = email.ai_suggested_assignee
        if old_val and old_val.strip():
            email.ai_suggested_assignee = json.dumps({"name": old_val.strip()})
        else:
            email.ai_suggested_assignee = "{}"
        email.save(update_fields=["ai_suggested_assignee"])


def reverse_assignee(apps, schema_editor):
    """Convert JSON back to plain string."""
    import json

    Email = apps.get_model("emails", "Email")
    for email in Email.objects.all():
        try:
            data = json.loads(email.ai_suggested_assignee)
            email.ai_suggested_assignee = data.get("name", "")
        except (json.JSONDecodeError, TypeError, AttributeError):
            email.ai_suggested_assignee = ""
        email.save(update_fields=["ai_suggested_assignee"])


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0003_activitylog"),
    ]

    operations = [
        migrations.RunPython(convert_assignee_to_json, reverse_assignee),
    ]
