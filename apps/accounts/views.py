"""Authentication views for VIPL Email Agent v2."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    """Placeholder dashboard view -- protected by login."""

    template_name = "accounts/dashboard.html"
