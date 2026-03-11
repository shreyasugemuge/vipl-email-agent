from django.urls import path

from . import views

app_name = "emails"

urlpatterns = [
    path("", views.email_list, name="email_list"),
    path("<int:pk>/detail/", views.email_detail, name="email_detail"),
    path("<int:pk>/assign/", views.assign_email_view, name="assign_email"),
    path("<int:pk>/status/", views.change_status_view, name="change_status"),
    path("inspect/", views.inspect, name="inspect"),
]
