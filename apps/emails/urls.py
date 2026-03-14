from django.urls import path

from . import views

app_name = "emails"

urlpatterns = [
    path("", views.email_list, name="email_list"),
    path("<int:pk>/detail/", views.email_detail, name="email_detail"),
    path("<int:pk>/assign/", views.assign_email_view, name="assign_email"),
    path("<int:pk>/status/", views.change_status_view, name="change_status"),
    path("<int:pk>/claim/", views.claim_email_view, name="claim_email"),
    path("<int:pk>/accept-ai/", views.accept_ai_suggestion, name="accept_ai_suggestion"),
    path("<int:pk>/reject-ai/", views.reject_ai_suggestion, name="reject_ai_suggestion"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/rules/", views.settings_rules_save, name="settings_rules_save"),
    path("settings/visibility/", views.settings_visibility_save, name="settings_visibility_save"),
    path("settings/sla/", views.settings_sla_save, name="settings_sla_save"),
    path("settings/inboxes/", views.settings_inboxes_save, name="settings_inboxes_save"),
    path("settings/config/", views.settings_config_save, name="settings_config_save"),
    path("settings/webhooks/", views.settings_webhooks_save, name="settings_webhooks_save"),
    path("settings/whitelist/add/", views.whitelist_add, name="whitelist_add"),
    path("settings/whitelist/<int:pk>/delete/", views.whitelist_delete, name="whitelist_delete"),
    path("activity/", views.activity_log, name="activity_log"),
    path("inspect/", views.inspect, name="inspect"),
]
