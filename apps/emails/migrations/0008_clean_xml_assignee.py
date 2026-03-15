"""Data migration to clean XML markup from ai_suggested_assignee field.

Some Claude API responses wrapped assignee names in XML parameter tags like:
<parameter name="name">Shreyas</parameter>

This migration strips those tags from existing records.
"""

import re

from django.db import migrations


def clean_xml_from_assignee(apps, schema_editor):
    """Clean XML tags from ai_suggested_assignee 'name' field in existing records."""
    Email = apps.get_model("emails", "Email")
    cleaned_count = 0

    for email in Email.objects.exclude(ai_suggested_assignee__exact={}):
        suggestion = email.ai_suggested_assignee
        if not isinstance(suggestion, dict):
            continue
        name = suggestion.get("name", "")
        if not name or "<" not in name:
            continue

        # Strip <parameter name="...">...</parameter> wrappers
        cleaned = re.sub(r'<parameter\s+name="[^"]*">(.*?)</parameter>', r'\1', name)
        # Fallback: strip any remaining XML-like tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = cleaned.strip()

        if cleaned != name:
            suggestion["name"] = cleaned
            email.ai_suggested_assignee = suggestion
            email.save(update_fields=["ai_suggested_assignee"])
            cleaned_count += 1

    if cleaned_count:
        print(f"\n  Cleaned XML from {cleaned_count} ai_suggested_assignee record(s)")


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0007_spamwhitelist"),
    ]

    operations = [
        migrations.RunPython(clean_xml_from_assignee, migrations.RunPython.noop),
    ]
