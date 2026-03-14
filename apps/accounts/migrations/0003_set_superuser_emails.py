"""Data migration: set email on existing superusers with blank email.

This prevents allauth email validation from breaking existing superuser accounts.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(is_superuser=True, email=""):
        user.email = f"{user.username}@vidarbhainfotech.com"
        user.save(update_fields=["email"])


def backwards(apps, schema_editor):
    pass  # No-op reverse


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_avatar_url"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
