from django.urls import path
from . import views

app_name = "emails"

urlpatterns = [
    path("", views.email_list, name="email_list"),
    path("inspect/", views.inspect, name="inspect"),
]
