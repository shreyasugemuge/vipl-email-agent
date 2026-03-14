"""Accounts URL configuration."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "dev-login/",
        views.dev_login,
        name="dev_login",
    ),
    path("team/", views.team_list, name="team"),
    path("team/<int:pk>/toggle-active/", views.toggle_active, name="toggle_active"),
    path("team/<int:pk>/change-role/", views.change_role, name="change_role"),
    path("team/<int:pk>/toggle-visibility/", views.toggle_visibility, name="toggle_visibility"),
    path("team/<int:pk>/categories/", views.save_categories, name="save_categories"),
]
