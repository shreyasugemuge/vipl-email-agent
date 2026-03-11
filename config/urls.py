"""Root URL configuration for VIPL Email Agent v2."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("emails/", include("apps.emails.urls")),
    path("", include("apps.core.urls")),
]
