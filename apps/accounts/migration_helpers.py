"""Helper for data migration: set email on superusers with blank email."""


def set_superuser_emails(User):
    """Set email = username@vidarbhainfotech.com on superusers with blank email."""
    for user in User.objects.filter(is_superuser=True, email=""):
        user.email = f"{user.username}@vidarbhainfotech.com"
        user.save(update_fields=["email"])
