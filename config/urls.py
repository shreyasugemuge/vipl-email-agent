"""Root URL configuration for VIPL Email Agent v2."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/dashboard/",
        RedirectView.as_view(url="/emails/", permanent=False),
        name="dashboard_redirect",
    ),
    path("accounts/", include("apps.accounts.urls")),
    path("emails/", include("apps.emails.urls")),
    path("", include("apps.core.urls")),
    path("", RedirectView.as_view(url="/emails/", permanent=False)),
]
