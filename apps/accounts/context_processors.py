"""Context processors for role-specific template variables."""


def user_permissions(request):
    """Add role-specific context for templates.

    Makes lead_categories available in all templates for sidebar category pills.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {}
    ctx = {}
    if request.user.role == "triage_lead":
        from apps.emails.models import AssignmentRule

        ctx["lead_categories"] = list(
            AssignmentRule.objects.filter(
                assignee=request.user, is_active=True
            ).values_list("category", flat=True)
        )
    return ctx
