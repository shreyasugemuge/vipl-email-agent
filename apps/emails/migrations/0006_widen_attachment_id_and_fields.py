"""Widen gmail_attachment_id (404+ chars in production) and from_name fields.

Gmail attachment IDs are base64-encoded and can exceed 400 characters.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0005_email_sla_ack_deadline_email_sla_respond_deadline_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachmentmetadata',
            name='gmail_attachment_id',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
        migrations.AlterField(
            model_name='attachmentmetadata',
            name='filename',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='email',
            name='from_name',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
